"""Milestone 5: report export navigates conclusion → evidence → shot; query; term proposals; gc; golden selftest."""

import json
from pathlib import Path

import pytest

from iris import analyze, claims, ingest, interpret, report, review_sheet
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
    p = ws / "grok.json"
    p.write_text(json.dumps(fx))
    assert interpret.ingest_answer(asset_id, p, "grok", workspace=ws)["ok"]
    interpret.run(asset_id, "fixture", workspace=ws)
    assert claims.validate_asset(asset_id, workspace=ws)["ok"]
    return asset_id


def test_report_links_every_conclusion_to_its_evidence_and_back(ws, judged):
    review_sheet.auto_accept(judged, workspace=ws)
    res = report.export(judged, workspace=ws)
    assert res["ok"] and not res["broken_links"] and res["claims"] > 0
    page = Path(res["path"]).read_text()
    cs = claims.list_claims(judged, workspace=ws)
    cited = next(c for c in cs if c.get("evidence_ids"))
    eid = cited["evidence_ids"][0]
    assert f'href="#{report._anchor(eid)}"' in page and f'id="{report._anchor(eid)}"' in page
    assert f'href="#claim-{cited["claim_id"]}"' in page  # evidence links back to the claim
    assert 'id="shot-s001"' in page and "data:image/jpeg;base64," in page


def test_report_cli_writes_to_output(ws, judged, capsys):
    out = ws / "exported"
    assert main(["report", "export", judged, "--output", str(out)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] and (out / "index.html").exists()


def test_query_filters_claims_and_searches_captions(ws, judged):
    review_sheet.auto_accept(judged, workspace=ws)
    from iris import query

    allc = query.query(workspace=ws)
    some = allc["claims"][0]
    res = query.query(term=some["term"], workspace=ws)
    assert res["claims_total"] >= 1 and all(c["term"] == some["term"] for c in res["claims"])
    bare = query.query(term=some["term"].split("=", 1)[1], dimension=some["term"].split("=", 1)[0], workspace=ws)
    assert bare["claims_total"] == res["claims_total"]
    hits = query.query(fts="one frame", workspace=ws)
    assert hits["claims_total"] == 0 and any(h["kind"] == "caption" and h["text"] == "ONE FRAME" for h in hits["text_hits"])
    assert query.query(fts="flying saucer", workspace=ws)["text_hits"] == []
    with_claims = query.query(dimension=some["term"].split("=", 1)[0], fts="one frame", workspace=ws)
    assert with_claims["claims_total"] >= 1


def _obs(ws, aid, dim, text, judge="grok"):
    p = ws / "refs" / aid / "interpret" / "observations.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    (ws / "refs" / aid / "manifest.json").exists() or (ws / "refs" / aid / "manifest.json").write_text("{}")
    with p.open("a") as fh:
        fh.write(json.dumps({"ts": "t", "asset_id": aid, "judge": judge, "unit_id": "s001", "dimension": dim, "observation": text}) + "\n")


def test_observations_recurring_in_three_references_become_a_proposal(ws):
    from iris import query

    _obs(ws, "ref_a", "light.scheme", "Warm tungsten practicals glow in the background")
    _obs(ws, "ref_b", "light.scheme", "tungsten practicals visible behind the subject", judge="anthropic")
    _obs(ws, "ref_c", "light.scheme", "Small tungsten practicals in frame")
    _obs(ws, "ref_c", "light.scheme", "hard light from the left")  # 'hard light' is already a term elsewhere; one ref anyway
    _obs(ws, "ref_a", "camera.movement", "tungsten practicals")  # other dimension: counted apart
    res = query.term_proposals(workspace=ws)
    props = [(p["dimension"], p["phrase"]) for p in res["proposals"]]
    assert ("light.scheme", "tungsten practicals") in props
    assert ("light.scheme", "tungsten") not in props and ("light.scheme", "practicals") not in props  # folded into the longer phrase
    assert not any(d == "camera.movement" for d, _ in props)
    doc = json.loads((ws / "proposals" / "term_proposals.json").read_text())
    assert doc["proposed_for"].endswith(".0") and doc["proposals"][0]["n_refs"] == 3


def test_gc_deletes_only_old_downloaded_originals_and_saves_cited_frames(ws, judged, monkeypatch):
    from iris import gc

    ref = ws / "refs" / judged
    m = json.loads((ref / "manifest.json").read_text())
    # pretend it was downloaded 100 days ago: the original lives in the reference directory
    src = ref / "source.mp4"
    src.write_bytes(Path(m["stored_path"]).read_bytes())
    m.update(stored_path=str(src), source={"kind": "url", "input": "https://example.com/v", "platform": None}, created_at="2020-01-01T00:00:00+00:00")
    (ref / "manifest.json").write_text(json.dumps(m))
    review_sheet.auto_accept(judged, workspace=ws)
    (ref / "work").mkdir(exist_ok=True)

    dry = gc.run(workspace=ws)
    assert not dry["applied"] and [r["asset_id"] for r in dry["originals_to_delete"]] == [judged] and src.exists()
    young = gc.run(keep_days=100000, workspace=ws)
    assert young["originals_to_delete"] == [] and young["originals_kept"][0]["reason"].startswith("younger")

    done = gc.run(apply=True, workspace=ws)
    assert done["ok"] and not src.exists() and (ref / "gc.jsonl").exists()
    assert gc.frame_path(ref, "s001", "mid").exists()
    for f in ("shots.json", "text.json", "color.json"):
        assert (ref / f).exists()  # evidence is never collected
    assert "data:image/jpeg;base64," in Path(report.export(judged, workspace=ws)["path"]).read_text()


def test_gc_keeps_references_of_an_approved_bible(ws, judged):
    from iris import gc

    ref = ws / "refs" / judged
    m = json.loads((ref / "manifest.json").read_text())
    src = ref / "source.mp4"
    src.write_bytes(Path(m["stored_path"]).read_bytes())
    m.update(stored_path=str(src), source={"kind": "url", "input": "https://example.com/v"}, created_at="2020-01-01T00:00:00+00:00")
    (ref / "manifest.json").write_text(json.dumps(m))
    (ws / "styles" / "s1").mkdir(parents=True)
    (ws / "styles" / "s1" / "style_bible.json").write_text(json.dumps({"style_id": "s1", "status": "approved", "built_from": [judged]}))
    res = gc.run(apply=True, workspace=ws)
    assert src.exists() and "approved Style Bible s1" in res["originals_kept"][0]["reason"]


def test_local_files_are_never_collected(ws, judged):
    from iris import gc

    m = json.loads((ws / "refs" / judged / "manifest.json").read_text())
    m["created_at"] = "2020-01-01T00:00:00+00:00"
    (ws / "refs" / judged / "manifest.json").write_text(json.dumps(m))
    res = gc.run(apply=True, workspace=ws)
    assert res["originals_deleted"] == [] and Path(m["stored_path"]).exists()


def test_golden_freeze_then_check_passes_and_detects_a_change(ws, judged, tmp_path):
    from iris import golden

    gdir = tmp_path / "golden"
    fr = golden.freeze(judged, workspace=ws, golden_dir=gdir)
    assert fr["source"]["fixture"] == "synthetic/caption_1frame.mp4"
    res = golden.check(workspace=ws, golden_dir=gdir)
    assert res["ok"] and res["passed"] == 1, res
    g = json.loads(Path(fr["path"]).read_text())
    g["facts"]["shots.count"] = 7
    g["facts"]["text.blocks"] = ["TWO FRAMES"]
    Path(fr["path"]).write_text(json.dumps(g))
    bad = golden.check(workspace=ws, golden_dir=gdir)
    assert not bad["ok"] and {d["fact"] for d in bad["failed"][0]["diffs"]} == {"shots.count", "text.blocks"}


def test_golden_skips_stage_with_another_backend_and_missing_sources(ws, judged, tmp_path):
    from iris import golden

    frozen, b = golden.facts(ws / "refs" / judged)
    other = dict(frozen, **{"text.blocks": ["something else"]})
    cmp = golden.compare(other, dict(b, text="another-ocr"), frozen, b)
    assert not cmp["diffs"] and any(s["fact"] == "text.blocks" for s in cmp["skipped_facts"])
    gdir = tmp_path / "golden"
    (gdir / "real").mkdir(parents=True)
    (gdir / "real" / "golden.json").write_text(json.dumps({"name": "real", "source": {"sha256": "0" * 64}, "facts": {}}))
    res = golden.check(workspace=ws, golden_dir=gdir)
    assert res["skipped"][0]["reason"] == "reference not in this workspace"
