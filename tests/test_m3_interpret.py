"""Milestone 3: packet, judges, fusion, validation, review, ledger. No API calls: the fixture provider and
hand-written answers stand in for the models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iris import analyze, anthropic_adapter, claims, ingest, interpret, ledger, registry
from iris.cli import main

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("IRIS_WORKSPACE", str(tmp_path))
    return tmp_path


@pytest.fixture
def analyzed(ws):
    r = ingest.ingest(str(FIX / "caption_1frame.mp4"), "own", workspace=ws)
    analyze.analyze(r["asset_id"], workspace=ws)
    return r["asset_id"]


def _j(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_prepare_writes_packet_with_images_and_evidence(ws, analyzed):
    res = interpret.prepare(analyzed, "anthropic", workspace=ws)
    assert res["windows"] == 1 and res["images"] >= 1
    pk = interpret.load_packet(analyzed, ws)
    assert pk["packet_hash"] == res["packet_hash"] and len(pk["packet_hash"]) == 64
    w = pk["windows"][0]
    assert w["shot_ids"] == ["s001"]
    assert any(e.startswith("keyframe:s001:") for e in w["evidence_ids"])
    for img in w["images"]:
        assert (ws / "refs" / analyzed / img["path"]).exists() and len(img["sha256"]) == 64
    assert set(pk["lexicon"]) == set(interpret.SHOT_DIMENSIONS + interpret.VIDEO_DIMENSIONS)
    assert (ws / "refs" / analyzed / "evidence.json").exists()
    assert all(i["width"] > 0 and i["height"] > 0 for i in w["images"])
    assert res["anthropic_estimate"]["worst_case_usd"] >= res["anthropic_estimate"]["expected_usd"] > 0
    # one packet serves both judges: the grok profile reads a subset and the hash does not change
    res_g = interpret.prepare(analyzed, "grok", workspace=ws)
    assert res_g["packet_hash"] == res["packet_hash"] and res_g["image_list"] == "images_grok"
    pk = interpret.load_packet(analyzed, ws)
    assert all(len(w["images_grok"]) <= interpret.MAX_IMAGES_GROK for w in pk["windows"])
    assert all(i in w["images"] for w in pk["windows"] for i in w["images_grok"])


def test_run_requires_grok_unless_skipped_and_fixture_spends_nothing(ws, analyzed):
    interpret.prepare(analyzed, workspace=ws)
    with pytest.raises(interpret.InterpretError):
        interpret.run(analyzed, "fixture", workspace=ws)
    res = interpret.run(analyzed, "fixture", skip_grok=True, workspace=ws)
    assert res["ok"] and res["cost_usd"] == 0.0 and res["shots_answered"] == 1
    cov = _j(ws / "refs" / analyzed / "coverage.json")
    assert cov["model_exposure"]["judge"] == "fixture"
    assert ledger.spent(ws) == 0.0


def _grok_answer(ws, asset_id, overrides):
    pk = interpret.load_packet(asset_id, ws)
    fx = interpret._fixture_answer(pk, None)
    fx["judge"] = "grok"
    for did, lab in overrides.items():
        fx["shots"][0]["dimensions"][did] = lab
    p = ws / "grok.json"
    p.write_text(json.dumps(fx))
    return p


def test_ingest_rejects_unknown_terms_wrong_hash_and_foreign_evidence(ws, analyzed):
    interpret.prepare(analyzed, workspace=ws)
    p = _grok_answer(ws, analyzed, {"optics": {"terms": ["bokeh_lens"], "evidence_ids": ["nope"]},
                                    "light.direction": {"terms": ["side_light", "backlight"], "evidence_ids": ["shot:s001"]}})
    res = interpret.ingest_answer(analyzed, p, "grok", workspace=ws)
    assert not res["ok"]
    msgs = " ".join(res["errors"])
    assert "unknown term 'bokeh_lens'" in msgs and "'nope' is not in the packet" in msgs and "exactly one term" in msgs
    good = json.loads(p.read_text())
    good["shots"][0]["dimensions"]["optics"] = {"terms": ["deep_focus"], "evidence_ids": ["shot:s001"]}
    good["shots"][0]["dimensions"]["light.direction"] = {"terms": ["unclear"], "evidence_ids": []}
    good["packet_hash"] = "0" * 64
    p.write_text(json.dumps(good))
    res = interpret.ingest_answer(analyzed, p, "grok", workspace=ws)
    assert not res["ok"] and any("packet_hash" in e for e in res["errors"])


def test_fusion_agreement_disagreement_and_single_judge(ws, analyzed):
    interpret.prepare(analyzed, workspace=ws)
    p = _grok_answer(ws, analyzed, {
        "style.medium": {"terms": ["motion_graphics"], "evidence_ids": ["shot:s001"], "observation": "flat beige card"},
        "optics": {"terms": ["deep_focus"], "evidence_ids": ["shot:s001"]},
    })
    assert interpret.ingest_answer(analyzed, p, "grok", workspace=ws)["ok"]
    interpret.run(analyzed, "fixture", workspace=ws)  # fixture says photorealistic, unclear on optics
    rep = claims.validate_asset(analyzed, workspace=ws)
    assert rep["ok"] and rep["rejected_by_validator"] == 0
    rows = {c["term_id"]: c for c in claims.list_claims(analyzed, workspace=ws)}
    assert rows["style.medium=motion_graphics"]["review_status"] == "needs_review"
    assert rows["style.medium=photorealistic"]["review_status"] == "needs_review"
    assert rows["style.medium=motion_graphics"]["disagreement_group"] == rows["style.medium=photorealistic"]["disagreement_group"]
    assert rows["optics=deep_focus"]["single_judge"] is True and rows["optics=deep_focus"]["review_status"] == "pending"
    assert all(c["claim_kind"] == "interpreted" for c in rows.values() if c["source"] == "model")
    assert all(c["evidence_ids"] for c in rows.values())
    assert rep["agreement"]["units_compared"] == 9 and rep["agreement"]["disagree"] == 1
    obs = (ws / "refs" / analyzed / "interpret" / "observations.jsonl").read_text().splitlines()
    assert any("flat beige card" in line for line in obs)
    # observations never become claims
    assert not any("beige" in json.dumps(c) for c in rows.values())


def test_code_claims_resolve_in_registry_and_cite_existing_evidence(ws, analyzed):
    rep = claims.validate_asset(analyzed, workspace=ws)
    rows = claims.list_claims(analyzed, source="code", workspace=ws)
    assert rows and all(registry.resolve(c["term_id"]) for c in rows)
    idx = _j(ws / "refs" / analyzed / "evidence.json")["evidence"]
    assert all(e in idx for c in rows for e in c["evidence_ids"])
    assert rep["by_source"]["code"] == len(rows)


def test_review_batch_is_append_only_and_survives_revalidation(ws, analyzed):
    rep = claims.validate_asset(analyzed, workspace=ws)
    ids = [c["claim_id"] for c in claims.list_claims(analyzed, workspace=ws)]
    assert len(ids) >= 3
    batch = ws / "batch.txt"
    batch.write_text(f"accept {ids[0]}-{ids[1]}\nreject {ids[2]}: not a pan, the caption insert fooled the estimator\n# comment\n")
    rc = main(["review", "--batch", str(batch), "--author", "tester", "--workspace", str(ws)])
    assert rc == 0
    rows = {c["claim_id"]: c for c in claims.list_claims(analyzed, workspace=ws)}
    assert rows[ids[0]]["review_status"] == "accepted" and rows[ids[2]]["review_status"] == "rejected"
    # a rejection without reason is refused; a correction to another dimension is refused
    res = claims.apply_decisions([{"claim_id": ids[1], "status": "rejected", "value": None, "reason": None}], "tester", workspace=ws)
    assert not res["ok"] and "reason" in res["errors"][0]["error"]
    res = claims.apply_decisions([{"claim_id": ids[0], "status": "corrected", "value": "style.medium=photorealistic", "reason": "x"}], "tester", workspace=ws)
    assert not res["ok"] and "belongs to" in res["errors"][0]["error"]
    rep2 = claims.validate_asset(analyzed, workspace=ws)
    rows2 = {c["claim_id"]: c for c in claims.list_claims(analyzed, workspace=ws)}
    assert rows2[ids[0]]["review_status"] == "accepted" and rows2[ids[2]]["review_status"] == "rejected"
    assert rep2["claims"] == rep["claims"]
    from iris.store import Store

    st = Store(ws)
    try:
        events = st.review_events()
    finally:
        st.close()
    assert len(events) == 3 and all(e["author"] == "tester" for e in events)


def test_parse_batch_lines():
    assert claims.parse_batch_line("accept c_000012-c_000014") == [{"claim_id": f"c_{i:06d}", "status": "accepted", "value": None, "reason": None} for i in (12, 13, 14)]
    d = claims.parse_batch_line("correct c_000044 to camera.movement=dolly_in: clear parallax")
    assert d == [{"claim_id": "c_000044", "status": "corrected", "value": "camera.movement=dolly_in", "reason": "clear parallax"}]
    with pytest.raises(claims.ClaimsError):
        claims.parse_batch_line("correct c_000044: no value")
    with pytest.raises(claims.ClaimsError):
        claims.parse_batch_line("maybe c_000001")


def test_ledger_budget_guard(ws, monkeypatch):
    ledger.record({"asset_id": "ref_000000000001", "model": "claude-sonnet-5-5", "cost_usd": 1.2, "usage": {"input_tokens": 1000, "output_tokens": 100}}, ws)
    ledger.record({"asset_id": "ref_000000000001", "model": "claude-sonnet-5-5", "cost_usd": 0.4, "usage": {}}, ws)
    ok, reason = ledger.check_budget("ref_000000000001", 1.5, ws)
    assert not ok and "per-reference cap" in reason
    ok, _ = ledger.check_budget("ref_000000000002", 1.5, ws)
    assert ok
    s = ledger.summary(ws)
    assert s["calls"] == 2 and abs(s["cost_usd"] - 1.6) < 1e-9 and s["by_model"]["claude-sonnet-5-5"]["input_tokens"] == 1000


def test_cli_interpret_and_validate_exit_codes(ws, analyzed, capsys):
    assert main(["interpret", "prepare", analyzed, "--workspace", str(ws)]) == 0
    assert main(["interpret", "run", analyzed, "--provider", "fixture", "--workspace", str(ws)]) == 3  # grok missing -> validation
    assert main(["interpret", "run", analyzed, "--provider", "fixture", "--skip-grok", "--workspace", str(ws)]) == 0
    assert main(["validate", analyzed, "--workspace", str(ws)]) == 0
    assert main(["claims", "list", analyzed, "--source", "model", "--workspace", str(ws)]) == 0
    out = capsys.readouterr().out
    assert '"count"' in out
    assert main(["ledger", "summary", "--workspace", str(ws)]) == 0
    assert main(["interpret", "run", "ref_000000000000", "--provider", "fixture", "--skip-grok", "--workspace", str(ws)]) in (3, 8)


def _fake_api(monkeypatch, ws, asset_id, calls):
    monkeypatch.setattr(anthropic_adapter, "load_api_key", lambda w: "sk-test-not-a-key")
    monkeypatch.setattr(anthropic_adapter, "make_client", lambda key: object())

    def judge(client, model, system, content, schema, repair_errors=None, previous_json=None):
        calls.append({"model": model, "images": sum(1 for b in content if b["type"] == "image"), "repair": bool(repair_errors)})
        fx = interpret._fixture_answer(interpret.load_packet(asset_id, ws), None)
        body = {"shots": fx["shots"], "video": fx["video"]}
        return {"json": body, "text": json.dumps(body), "usage": {"input_tokens": 6000, "output_tokens": 1500, "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 2000}, "request_id": "req_test", "model": model, "stop_reason": "end_turn", "error": None}

    monkeypatch.setattr(anthropic_adapter, "judge_window", judge)


def test_anthropic_branch_budget_rerun_and_stale_grok(ws, analyzed, monkeypatch):
    interpret.prepare(analyzed, "grok", workspace=ws)
    p = _grok_answer(ws, analyzed, {})
    assert interpret.ingest_answer(analyzed, p, "grok", workspace=ws)["ok"]
    calls: list[dict] = []
    _fake_api(monkeypatch, ws, analyzed, calls)
    # a cap below the ceiling of one call refuses before any request is sent
    with pytest.raises(interpret.InterpretError) as exc:
        interpret.run(analyzed, "anthropic", max_usd=0.01, workspace=ws)
    assert exc.value.code == "budget_exhausted" and calls == []
    res = interpret.run(analyzed, "anthropic", workspace=ws)
    assert res["ok"] and res["calls"] == 1 and res["model"] == "claude-sonnet-5-5"
    pk = interpret.load_packet(analyzed, ws)
    assert calls[0]["images"] == len(pk["windows"][0]["images"])  # the API judge sees the full image list
    rows = ledger.entries(ws)
    assert len(rows) == 1 and rows[0]["cost_usd"] == res["cost_usd"] > 0 and "sk-test" not in json.dumps(rows)
    # paying twice for the same packet needs --rerun
    with pytest.raises(interpret.InterpretError):
        interpret.run(analyzed, "anthropic", workspace=ws)
    rep = claims.validate_asset(analyzed, workspace=ws)
    assert rep["judges_present"] == ["anthropic", "grok"] and rep["agreement"]["units_compared"] == 9
    # a grok answer to an older packet blocks the paid judge
    g = ws / "refs" / analyzed / "interpret" / "grok.json"
    doc = json.loads(g.read_text()); doc["packet_hash"] = "f" * 64; g.write_text(json.dumps(doc))
    with pytest.raises(interpret.InterpretError) as exc:
        interpret.run(analyzed, "anthropic", rerun=True, workspace=ws)
    assert "older packet" in str(exc.value) and len(calls) == 1


def test_budget_reserve_never_passes_cap(ws):
    ledger.record({"asset_id": "ref_000000000003", "model": "claude-sonnet-5-5", "cost_usd": 1.40, "usage": {}}, ws)
    assert ledger.check_budget("ref_000000000003", 1.5, ws, reserve_usd=0.05)[0]
    ok, reason = ledger.check_budget("ref_000000000003", 1.5, ws, reserve_usd=0.11)
    assert not ok and "reserved" in reason


def test_window_schema_uses_only_keywords_the_api_accepts(ws, analyzed):
    interpret.prepare(analyzed, workspace=ws)
    pk = interpret.load_packet(analyzed, ws)
    text = json.dumps(interpret._window_schema(pk["windows"][0], pk, True))
    for kw in ("maxItems", "maxLength", "minLength", "pattern", "maximum", "minimum"):
        assert f'"{kw}"' not in text, kw
