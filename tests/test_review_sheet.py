"""Review by exception: statements from agreement, questions only for disputes that change the result,
one answer line applied once."""

import json
from pathlib import Path

import pytest

from iris import analyze, claims, ingest, interpret, review_sheet
from iris.cli import main

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("IRIS_WORKSPACE", str(tmp_path))
    return tmp_path


@pytest.fixture
def judged(ws):
    asset_id = ingest.ingest(str(FIX / "caption_1frame.mp4"), "own", workspace=ws)["asset_id"]
    analyze.analyze(asset_id, workspace=ws)
    interpret.prepare(asset_id, workspace=ws)
    fx = interpret._fixture_answer(interpret.load_packet(asset_id, ws), None)
    fx["judge"] = "grok"
    fx["shots"][0]["dimensions"]["style.medium"] = {"terms": ["motion_graphics"], "evidence_ids": ["shot:s001"]}
    fx["shots"][0]["dimensions"]["optics"] = {"terms": ["deep_focus"], "evidence_ids": ["shot:s001"]}
    fx["shots"][0]["dimensions"]["light.direction"] = {"terms": ["side_light"], "evidence_ids": ["shot:s001"]}
    p = ws / "grok.json"
    p.write_text(json.dumps(fx))
    assert interpret.ingest_answer(asset_id, p, "grok", workspace=ws)["ok"]
    second = interpret._fixture_answer(interpret.load_packet(asset_id, ws), None)
    second["shots"][0]["dimensions"]["light.direction"] = {"terms": ["side_light"], "evidence_ids": ["shot:s001"]}
    f2 = ws / "second.json"
    f2.write_text(json.dumps(second))
    # photorealistic vs motion_graphics; both say side light; unclear on optics
    interpret.run(asset_id, "fixture", fixture_file=f2, workspace=ws)
    assert claims.validate_asset(asset_id, workspace=ws)["ok"]
    return asset_id


def test_sheet_asks_only_the_dispute_and_folds_agreement_into_statements(ws, judged):
    res = review_sheet.make_sheet(judged, workspace=ws)
    sheet = json.loads((ws / "refs" / judged / "review" / "sheet.json").read_text())
    qs = [i for i in sheet["items"] if i["kind"] == "question"]
    assert res["questions"] == 1 and qs[0]["dimension"] == "style.medium" and {qs[0]["a"], qs[0]["b"]} == {"motion_graphics", "photorealistic"}
    assert all(i["default"] == "y" for i in sheet["items"] if i["kind"] == "statement")
    assert not any(i["dimension"] == "optics" for i in sheet["items"])  # one judge only: not asked
    assert any(x["dimension"] == "optics" for x in sheet["not_asked"])
    html = Path(res["html"]).read_text()
    assert f"iris-review {judged} {sheet['sheet_id']} " in html and "data:image/jpeg;base64," in html


def test_answer_line_applies_once_and_maps_choices(ws, judged):
    sheet = review_sheet.build_items(judged, workspace=ws)
    codes = "".join("a" if i["kind"] == "question" else "y" for i in sheet["items"])
    q = next(i for i in sheet["items"] if i["kind"] == "question")
    line = f"iris-review {judged} {sheet['sheet_id']} {codes}"
    res = review_sheet.apply_answer(line, "bruno", workspace=ws)
    assert res["ok"] and res["answers"]["chosen"] == 1 and res["recorded"]["rejected"] == len(q["claim_ids"]["b"])
    rows = {c["claim_id"]: c for c in claims.list_claims(judged, workspace=ws)}
    assert all(rows[c]["review_status"] == "accepted" for c in q["claim_ids"]["a"])
    assert all(rows[c]["review_status"] == "rejected" for c in q["claim_ids"]["b"])
    with pytest.raises(review_sheet.SheetError, match="older sheet"):
        review_sheet.apply_answer(line, "bruno", workspace=ws)
    # what is left is only what nobody could settle: a new sheet has no statement left to confirm
    assert not [i for i in review_sheet.build_items(judged, workspace=ws)["items"] if i["kind"] == "statement"]


def test_bad_lines_are_refused(ws, judged):
    sheet = review_sheet.build_items(judged, workspace=ws)
    with pytest.raises(review_sheet.SheetError):
        review_sheet.apply_answer("accept everything", "bruno", workspace=ws)
    with pytest.raises(review_sheet.SheetError, match="answers"):
        review_sheet.apply_answer(f"iris-review {judged} {sheet['sheet_id']} y", "bruno", workspace=ws)
    assert main(["review", "--answer", "iris-review x 000000000000 y", "--workspace", str(ws)]) != 0
    assert main(["review-sheet", judged, "--workspace", str(ws)]) == 0


def _c(cid, dim, term, unit, status="pending", source="model", group=None, single=False, dur=1.0):
    return {"claim_id": cid, "dimension": dim, "term_id": f"{dim}={term}", "unit_id": unit, "review_status": status, "source": source,
            "claim_kind": "interpreted" if source == "model" else "estimated", "single_judge": single, "disagreement_group": group,
            "time_span": {"start_seconds": 0.0, "end_seconds": dur}}


def test_dispute_that_cannot_change_the_summary_is_not_asked(monkeypatch):
    rows = [_c(f"c_{i:06d}", "light.direction", "side_light", f"s{i:03d}") for i in range(1, 9)]
    # one shot disputed between front and back light: either way side light stays the top term and neither reaches 10%
    rows += [_c("c_000020", "light.direction", "front_light", "s020", "needs_review", group="s020|light.direction", dur=0.5),
             _c("c_000021", "light.direction", "backlight", "s020", "needs_review", group="s020|light.direction", dur=0.5)]
    # a real dispute in another dimension: half the runtime either way
    rows += [_c(f"c_0001{i:02d}", "style.medium", "photorealistic", f"s{i:03d}") for i in range(1, 3)]
    rows += [_c(f"c_0002{i:02d}", "style.medium", t, f"s1{i:02d}", "needs_review", group=f"s1{i:02d}|style.medium") for i in range(1, 4) for t in ("motion_graphics", "photorealistic")]
    rows += [_c("c_000300", "optics", "deep_focus", "s001", single=True)]
    monkeypatch.setattr(review_sheet.claims_mod, "list_claims", lambda asset_id, workspace=None: rows)
    sheet = review_sheet.build_items("ref_x")
    kinds = [(i["kind"], i["dimension"]) for i in sheet["items"]]
    assert ("question", "light.direction") not in kinds and ("statement", "light.direction") in kinds
    assert ("question", "style.medium") in kinds
    assert {x["dimension"] for x in sheet["not_asked"]} == {"light.direction", "optics"}


def test_both_only_where_the_dimension_takes_several_terms(ws, judged):
    sheet = review_sheet.build_items(judged, workspace=ws)
    q = next(i for i in sheet["items"] if i["kind"] == "question")
    assert q["dimension"] == "style.medium" and q["allow_both"] is False  # single-term dimension
    assert set(q["a_by"] + q["b_by"]) == {"Grok", "Fixture"}
    codes = "".join("z" if i["kind"] == "question" else "s" for i in sheet["items"])
    with pytest.raises(review_sheet.SheetError, match="takes a, b, x or s"):
        review_sheet.apply_answer(f"iris-review {judged} {sheet['sheet_id']} {codes}", "bruno", workspace=ws)
    html = Path(review_sheet.make_sheet(judged, workspace=ws)["html"]).read_text()
    assert "Fixture and Grok looked at the same shot and gave different answers" in html and "chose this" in html and 'data-v="z"' not in html


def test_both_accepts_both_terms_in_a_multi_term_dimension(monkeypatch):
    rows = [_c("c_000001", "composition", "symmetry", "s001")]
    for i in range(2, 5):
        rows += [dict(_c(f"c_0000{i}0", "composition", "centralbias", f"s00{i}", "needs_review", group=f"s00{i}|composition"), judges={"grok": "centralbias", "anthropic": "leadinglines"}),
                 dict(_c(f"c_0000{i}1", "composition", "leadinglines", f"s00{i}", "needs_review", group=f"s00{i}|composition"), judges={"grok": "centralbias", "anthropic": "leadinglines"})]
    monkeypatch.setattr(review_sheet.claims_mod, "list_claims", lambda asset_id, workspace=None: rows)
    applied = []
    monkeypatch.setattr(review_sheet.claims_mod, "apply_decisions", lambda d, author, workspace=None: applied.extend(d) or {"ok": True, "recorded": [], "errors": []})
    sheet = review_sheet.build_items("ref_x")
    q = next(i for i in sheet["items"] if i["kind"] == "question")
    assert q["allow_both"] and q["a_by"] == ["Grok"] and q["b_by"] == ["Claude"]
    codes = "".join("z" if i["kind"] == "question" else "s" for i in sheet["items"])
    res = review_sheet.apply_answer(f"iris-review ref_x {sheet['sheet_id']} {codes}", "bruno")
    assert res["answers"]["both"] == 1 and len(applied) == 6 and all(d["status"] == "accepted" for d in applied)


def test_judge_agreement_is_accepted_without_asking(ws, judged):
    agreed = [c["claim_id"] for c in claims.list_claims(judged, workspace=ws) if review_sheet.judges_agree(c)]
    assert agreed
    res = review_sheet.make_sheet(judged, workspace=ws)
    assert res["ok"] and res["auto_accepted"] == len(agreed)
    rows = {c["claim_id"]: c for c in claims.list_claims(judged, workspace=ws)}
    assert all(rows[c]["review_status"] == "accepted" for c in agreed)
    sheet = json.loads((ws / "refs" / judged / "review" / "sheet.json").read_text())
    assert all(i["source"] == "code" for i in sheet["items"] if i["kind"] == "statement")  # nothing the judges agreed on is asked again
    assert sheet["settled"] and "Already accepted" in Path(res["html"]).read_text()
    from iris.store import Store
    st = Store(ws)
    try:
        authors = {e["author"] for e in st.review_events(agreed[0])}
    finally:
        st.close()
    assert authors == {review_sheet.POLICY_AUTHOR}
    assert review_sheet.make_sheet(judged, workspace=ws)["auto_accepted"] == 0  # idempotent
