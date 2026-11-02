"""Milestone 4: Style Bible build / lint / approve and `iris check`. Synthetic fixtures only."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import jsonschema
import pytest

from iris import analyze, check, claims, continuity, ingest, paths, style
from iris.cli import main

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic"
FFMPEG = shutil.which("ffmpeg")


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("IRIS_WORKSPACE", str(tmp_path))
    return tmp_path


def _ref(ws, name):
    r = ingest.ingest(str(FIX / name), "own", workspace=ws)
    analyze.analyze(r["asset_id"], workspace=ws)
    claims.validate_asset(r["asset_id"], workspace=ws)
    return r["asset_id"]


def _decide(ws, asset_id, status="accepted", only=None):
    rows = [c for c in claims.list_claims(asset_id, workspace=ws) if only is None or c["dimension"] in only]
    res = claims.apply_decisions([{"claim_id": c["claim_id"], "status": status, "value": None, "reason": "test" if status == "rejected" else None} for c in rows], "tester", workspace=ws)
    assert res["ok"], res["errors"]
    return rows


def _schema(name):
    return json.loads((paths.SCHEMAS_DIR / f"{name}.schema.json").read_text())


def _bible(ws, sid):
    return json.loads((ws / "styles" / sid / "style_bible.json").read_text())


def test_single_reference_builds_a_provisional_draft_that_lints(ws):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    rep = style.build([a], "pan-test-v1", workspace=ws)
    assert rep["ok"] and rep["status"] == "draft" and rep["provisional"] and rep["tokens"] <= style.TOKEN_LIMIT
    b = _bible(ws, "pan-test-v1")
    assert not list(jsonschema.Draft202012Validator(_schema("style_bible")).iter_errors(b))
    assert b["provenance"]["default_tolerances"] == style.DEFAULT_TOLERANCES and a in b["provenance"]["inputs_sha256"]
    assert b["light"]["meta"]["provisional"] is True and b["color"]["regions"]["background"]["L"]["min"] < b["color"]["regions"]["background"]["L"]["typical"]
    # nothing is invented: prose blocks are empty, pending, and list what is missing
    assert b["concept"]["meta"]["review_status"] == "pending" and set(b["concept"]["meta"]["missing"]) == set(style.REQUIRED_V10["concept"])
    assert "concept" in rep["pending_blocks"] and rep["brief"] == "absent"
    assert b["camera"]["movement"] == {"pan_right": 1.0}
    assert len(b["continuity_rules"]) >= 3 and b["exemplars"]["color_master"][0]["ref"] == a
    assert style.lint("pan-test-v1", ws)["ok"]
    assert (ws / "styles" / "pan-test-v1" / "style_bible.md").read_text() == style.render_md(b)


def test_only_decided_claims_reach_the_bible(ws):
    a = _ref(ws, "pan_right.mp4")
    style.build([a], "undecided-v1", workspace=ws)
    b = _bible(ws, "undecided-v1")
    assert "movement" not in b["camera"] and "key" not in b["light"]
    _decide(ws, a, "rejected", only={"camera.movement"})
    _decide(ws, a, "accepted", only={"light.key", "light.side", "light.quality"})
    style.build([a], "undecided-v1", workspace=ws)
    b = _bible(ws, "undecided-v1")
    assert "movement" not in b["camera"] and b["light"]["key"].startswith("light.key.")
    cid = next(c["claim_id"] for c in claims.list_claims(a, workspace=ws) if c["dimension"] == "camera.movement")
    assert claims.apply_decisions([{"claim_id": cid, "status": "corrected", "value": "camera.movement=tracking_shot", "reason": "x"}], "tester", workspace=ws)["ok"]
    style.build([a], "undecided-v1", workspace=ws)
    b = _bible(ws, "undecided-v1")
    assert b["camera"]["movement"] == {"tracking_shot": 1.0} and b["camera"]["meta"]["review_status"] == "corrected"


def test_interpreted_terms_need_two_of_three_references(ws):
    ids = [_ref(ws, n) for n in ("pan_right.mp4", "push_in.mp4", "cfr_30.mp4")]
    for a in ids:
        _decide(ws, a)
    labels = {a: next(c for c in claims.list_claims(a, workspace=ws) if c["dimension"] == "camera.movement") for a in ids}
    # make two of three agree on pan_right
    pid = labels[ids[1]]["claim_id"]
    assert claims.apply_decisions([{"claim_id": pid, "status": "corrected", "value": "camera.movement=pan_right", "reason": "x"}], "tester", workspace=ws)["ok"]
    rep = style.build(ids, "three-v1", workspace=ws)
    b = _bible(ws, "three-v1")
    assert rep["ok"] and not rep["provisional"] and "default_tolerances" not in b["provenance"]
    assert list(b["camera"]["movement"]) == ["pan_right"]
    assert not b["light"]["meta"].get("provisional")
    assert len(rep["membership"]) == 3


def test_membership_warning_flags_an_outlier():
    refs = [{"asset_id": f"ref_000{i}"} for i in range(4)]
    base = {"duration_s": 30.0, "cuts_per_s.overall": 1.2, "shot_length_p50": 0.8, "loudness_lufs": -14.0, "background_L_p50": 80.0, "unique_pictures": 30.0}
    facts = {"ref_0000": dict(base), "ref_0001": {**base, "duration_s": 31.0}, "ref_0002": {**base, "loudness_lufs": -14.5},
             "ref_0003": {"duration_s": 90.0, "cuts_per_s.overall": 0.2, "shot_length_p50": 5.0, "loudness_lufs": -23.0, "background_L_p50": 20.0, "unique_pictures": 18.0}}
    mem = {m["asset_id"]: m for m in style.membership(refs, facts)}
    assert mem["ref_0003"]["warning"] and mem["ref_0003"]["share_outside"] > style.MEMBERSHIP_SHARE
    assert not mem["ref_0000"]["warning"]


def test_brief_fills_prose_and_is_validated(ws):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    sdir = ws / "styles" / "brief-test-v1"
    sdir.mkdir(parents=True)
    brief = json.loads((paths.SCHEMAS_DIR / "examples" / "style_brief.example.json").read_text())
    brief["style_id"] = "brief-test-v1"
    brief["identity"]["one_line"] = "Shot at 24 fps"  # digits in prose are refused
    (sdir / "brief.json").write_text(json.dumps(brief))
    with pytest.raises(style.StyleError, match="brief.json is invalid"):
        style.build([a], "brief-test-v1", workspace=ws)
    brief["identity"]["one_line"] = "Calm lateral travel across a quiet field."
    brief["never"]["camera"] = ["camera.movement.not_a_move"]
    (sdir / "brief.json").write_text(json.dumps(brief))
    with pytest.raises(style.StyleError, match="not in the vocabulary"):
        style.build([a], "brief-test-v1", workspace=ws)
    brief["never"]["camera"] = ["camera.movement.whip_pan"]
    reviewer = brief.pop("reviewed_by")
    (sdir / "brief.json").write_text(json.dumps(brief))
    rep = style.build([a], "brief-test-v1", workspace=ws)
    b = _bible(ws, "brief-test-v1")
    assert rep["brief"] == "unreviewed" and b["concept"]["meta"]["review_status"] == "pending"
    assert b["camera"]["never"] == ["camera.movement.whip_pan"] and b["never_global"] == ["montage.transition.wipe"]
    assert any(r["rule_id"] == "cr_peak_ceiling" and r["source"] == "brief" for r in b["continuity_rules"])
    assert main(["style", "approve-brief", "brief-test-v1", "--author", reviewer, "--workspace", str(ws)]) == 0
    assert json.loads((sdir / "brief.json").read_text())["reviewed_by"] == reviewer
    style.build([a], "brief-test-v1", workspace=ws)
    b = _bible(ws, "brief-test-v1")
    assert b["concept"]["meta"]["review_status"] == "accepted" and b["identity"]["one_line"].startswith("Calm")
    assert b["provenance"]["brief_sha256"] and style.lint("brief-test-v1", ws)["ok"]


def test_lint_catches_tampering_and_approve_needs_three_refs(ws):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    style.build([a], "lint-test-v1", workspace=ws)
    d = ws / "styles" / "lint-test-v1"
    md = d / "style_bible.md"
    md.write_text(md.read_text() + "\nhand edit\n")
    assert any("rendering" in i for i in style.lint("lint-test-v1", ws)["issues"])
    b = _bible(ws, "lint-test-v1")
    b["light"]["never"] = ["light.key.ultra_key"]
    (d / "style_bible.json").write_text(json.dumps(b, indent=1))
    issues = style.lint("lint-test-v1", ws)["issues"]
    assert any("not in the vocabulary" in i for i in issues) and any("sha256" in i for i in issues)
    style.build([a], "lint-test-v1", workspace=ws)
    res = style.approve("lint-test-v1", "tester", workspace=ws)
    assert not res["ok"] and any("at least 3 references" in x for x in res["blockers"])


def test_budget_trimming_keeps_rhythm_rules_and_never(ws, monkeypatch):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    full = style.build([a], "budget-v1", workspace=ws)["tokens"]
    monkeypatch.setattr(style, "TOKEN_LIMIT", full - 60)
    b = _bible(ws, "budget-v1")
    dropped = style.fit_budget(b)
    assert dropped and style.measure_tokens(b) <= full - 60
    assert b["rhythm"] and b["continuity_rules"] and all("never" in b[n] for n in style.VISUAL_NEVER)
    assert all(not x.startswith(("rhythm", "never")) for x in dropped)


def test_tolerance_parser():
    assert continuity.parse_tolerance("<= 6") == ("le", 6.0)
    assert continuity.parse_tolerance("within [-15.5, -12.5]") == ("within", -15.5, -12.5)
    assert continuity.parse_tolerance("within 0.027-0.032") == ("within", 0.027, 0.032)
    assert continuity.parse_tolerance("in {key_centred, key_screen_left}")[1] == frozenset({"key_centred", "key_screen_left"})
    assert continuity.satisfies(-14.0, ("within", -15.5, -12.5)) and not continuity.satisfies(7, ("le", 6.0))
    with pytest.raises(continuity.ToleranceError):
        continuity.parse_tolerance("about six")


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg not installed")
def test_check_passes_a_clip_of_the_same_video_and_fails_injected_colour(ws, tmp_path):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    sdir = ws / "styles" / "gate-v1"
    sdir.mkdir(parents=True)
    (sdir / "brief.json").write_text(json.dumps({"schema_version": "1.0.0", "style_id": "gate-v1", "never": {"camera": ["camera.movement.whip_pan"]},
        "continuity_rules": [{"rule_id": "cr_loud", "scope": "audio", "metric": "audio.integrated_lufs", "tolerance": "within [-16, -12]", "severity": "fail"}]}))
    rep = style.build([a], "gate-v1", workspace=ws)
    assert "cr_frame_delta_e" in rep["rules"]  # the background covers <20% of this frame
    same = tmp_path / "same.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(FIX / "pan_right.mp4"), "-t", "2", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(same)], check=True)
    shifted = tmp_path / "shifted.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(FIX / "pan_right.mp4"), "-t", "2", "-vf", "eq=brightness=0.15,colorbalance=rs=0.6:gs=-0.3:bs=-0.6:rm=0.6:gm=-0.3:bm=-0.6",
                    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(shifted)], check=True)
    ok = check.check(str(same), "gate-v1", workspace=ws)
    rules = {r["rule_id"]: r for r in ok["rules"]}
    assert ok["status"] in ("pass", "warn") and rules["cr_frame_delta_e"]["status"] == "pass"
    assert rules["cr_loud"]["status"] == "not_applicable"  # no audio stream: never a pass by absence
    assert {n["term"]: n["status"] for n in ok["never"]}["camera.movement.whip_pan"] == "pass"
    bad = check.check(str(shifted), "gate-v1", workspace=ws)
    r = {x["rule_id"]: x for x in bad["rules"]}["cr_frame_delta_e"]
    assert bad["status"] == "fail" and r["status"] == "fail" and r["violations"][0]["value"] > 10
    assert "frame" in r["violations"][0] and "t" in r["violations"][0]
    report = json.loads(Path(bad["report_path"]).read_text())
    assert not list(jsonschema.Draft202012Validator(_schema("continuity_report")).iter_errors(report))


def test_cli_style_and_check_exit_codes(ws, capsys):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    assert main(["style", "build", "--from", a, "--style-id", "cli-v1", "--workspace", str(ws)]) == 0
    assert main(["style", "lint", "cli-v1", "--workspace", str(ws)]) == 0
    assert main(["style", "approve", "cli-v1", "--author", "t", "--workspace", str(ws)]) == 3
    assert main(["style", "build", "--style-id", "cli-v1", "--workspace", str(ws)]) == 2
    assert main(["style", "lint", "missing-v1", "--workspace", str(ws)]) == 3
    assert main(["check", str(FIX / "pan_right.mp4"), "--against", "missing-v1", "--workspace", str(ws)]) == 3


def test_caption_cadence_counts_blocks_not_lines(ws):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    ref = ws / "refs" / a
    def tr(i, text, f0, f1, y):
        return {"track_id": f"t{i:04d}", "text": text, "conf": 0.97, "box_norm": [0.25, y, 0.75, y + 0.04], "zone": "lower_third", "rel_height": 0.04,
                "frame_first_seen": f0, "frame_last_seen": f1, "class": "subtitle_candidate", "animation": "build_on" if i == 0 else "static_or_cut",
                "reveal_steps": 2 if i == 0 else 0, "block_id": "b0000" if i < 2 else "b0001"}
    tracks = [tr(0, "He climbed onto a", 0, 54, 0.70), tr(1, "platform,", 24, 54, 0.75), tr(2, "and waited.", 60, 110, 0.72)]
    for t_, hexes in zip(tracks, [("#FFFFFF", "#101010"), ("#FAFAFA", "#121212"), ("#FFD400", "#111111")]):
        t_["style"] = {"text_hex": hexes[0], "back_hex": hexes[1], "backing": "solid"}
    blocks = [{"block_id": "b0000", "track_ids": ["t0000", "t0001"], "text": "He climbed onto a platform,", "lines": 2, "words": 5,
               "frame_first_seen": 0, "frame_last_seen": 54, "zone": "lower_third", "caption_like": True},
              {"block_id": "b0001", "track_ids": ["t0002"], "text": "and waited.", "lines": 1, "words": 2,
               "frame_first_seen": 60, "frame_last_seen": 110, "zone": "lower_third", "caption_like": True}]
    (ref / "text.json").write_text(json.dumps({"schema_version": "1.0.0", "method_version": "textocr@0.3.0", "status": "ok", "tracks": tracks, "blocks": blocks}))
    cov = json.loads((ref / "coverage.json").read_text())
    cov["stages"]["text"] = {"status": "ok"}
    (ref / "coverage.json").write_text(json.dumps(cov))
    rep = style.build([a], "caption-v1", workspace=ws)
    t = _bible(ws, "caption-v1")["typography"]
    assert rep["ok"] and t["lines"]["max"] == 2 and t["placement"]["zone"] == "lower_third" and t["case"] == "sentence"
    assert t["caption_cadence"]["words_per_cue"]["typical"] == 3.5
    assert t["placement"]["text_color"] == "#FCFCFC" and t["placement"]["box"] == "solid" and t["placement"]["x_align"] == "center"
    assert t["placement"]["box_color"] == "#111111"
    assert t["emphasis"] == {"word_reveal": round(1 / 3, 3)} and "cr_caption_zone" in rep["rules"]


def test_build_writes_a_style_board_of_screenshots_without_touching_the_bible(ws):
    a = _ref(ws, "pan_right.mp4")
    _decide(ws, a)
    rep = style.build([a], "board-v1", workspace=ws)
    v = rep["visual"]
    assert rep["ok"] and v["ok"] and v["screenshots"] >= 5 and not v["missing_frames"], v
    d = ws / "styles" / "board-v1"
    doc = json.loads((d / "visual" / "board.json").read_text())
    picks = [p for lst in doc["sections"].values() for p in lst]
    assert {"opening", "color", "camera", "screen_time"} <= set(doc["sections"]) and len(doc["sections"]["camera"]) == 3
    assert all(p["file"] and (d / p["file"]).exists() for p in picks) and any(p.get("bible_exemplar") for p in picks)
    assert (d / "style_board.html").read_text().count("data:image/jpeg;base64,") == v["screenshots"]
    assert doc["bible_sha256"] == (d / "style_bible.sha256").read_text().strip() and style.lint("board-v1", ws)["ok"]
    before = {p.name: p.stat().st_mtime_ns for p in (d / "visual").glob("*.jpg")}
    from iris import style_board
    assert style_board.build("board-v1", ws)["screenshots"] == v["screenshots"]
    assert {p.name: p.stat().st_mtime_ns for p in (d / "visual").glob("*.jpg")} == before  # screenshots are reused, not re-decoded
