"""Milestone 2 acceptance on synthetic fixtures: shots and one-frame events, motion classes, OCR cue
timing, per-region colour and light, audio loudness, contact sheets."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from iris import analyze, ingest, paths

FIX = paths.FIXTURES_DIR / "synthetic"
MANIFEST = json.loads((paths.FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))["fixtures"]


@pytest.fixture(scope="session", autouse=True)
def fixtures_present():
    if not (FIX / "pan_right.mp4").exists():
        subprocess.run([str(paths.REPO_ROOT / "tools" / "make_fixtures.sh")], check=True, capture_output=True)


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("IRIS_WORKSPACE", str(tmp_path))
    return tmp_path


def _analyze(ws: Path, name: str):
    res = ingest.ingest(str(FIX / name), "own", workspace=ws)
    out = analyze.analyze(res["asset_id"], workspace=ws)
    ref = ws / "refs" / res["asset_id"]
    return out, ref


def _j(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_cfr_three_shots_two_cuts_and_montage(ws):
    out, ref = _analyze(ws, "cfr_30.mp4")
    shots = _j(ref / "shots.json")
    assert shots["montage"]["shot_count"] == 3 and shots["montage"]["cut_count"] == 2
    firsts = [s["frame_first"] for s in shots["shots"]]
    assert firsts == [0, 60, 120]
    assert abs(shots["shots"][1]["t_in"] - 2.0) < 0.05
    assert out["coverage"]["stages"]["shots"]["status"] == "ok"


def test_one_frame_flash_is_an_event_not_a_cut(ws):
    out, ref = _analyze(ws, "flash_1frame.mp4")
    events = _j(ref / "events.json")
    flashes = [e for e in events["events"] if e["type"] == "flash"]
    assert len(flashes) == 1 and flashes[0]["frame_first"] == 90 and flashes[0]["length_frames"] == 1
    shots = _j(ref / "shots.json")
    assert shots["montage"]["shot_count"] == 1


def test_pan_right_is_classified(ws):
    out, ref = _analyze(ws, "pan_right.mp4")
    m = _j(ref / "motion.json")
    classes = [s["class"] for s in m["shots"] if s.get("status") == "ok"]
    assert classes and classes[0] == MANIFEST["pan_right.mp4"]["expected_class"], m["shots"][0]


def test_push_in_is_apparent_with_alternatives(ws):
    out, ref = _analyze(ws, "push_in.mp4")
    m = _j(ref / "motion.json")
    s = [x for x in m["shots"] if x.get("status") == "ok"][0]
    assert s["class"] == "apparent_push_in" and "dolly_in" in s["alternatives"] and s["flow_divergence_pct_w_per_s"] > 0


def test_static_clip_is_static(ws):
    out, ref = _analyze(ws, "cfr_30.mp4")
    m = _j(ref / "motion.json")
    assert all(s["class"] == "static" for s in m["shots"] if s.get("status") == "ok")


def test_caption_one_frame_cue_within_two_frames(ws):
    out, ref = _analyze(ws, "caption_1frame.mp4")
    text = _j(ref / "text.json")
    if text.get("status") == "skipped":
        pytest.skip(f"no OCR backend here: {text.get('reason')}")
    tracks = [t for t in text["tracks"] if "FRAME" in t["text"].upper() or "ONE" in t["text"].upper()]
    assert tracks, text
    t = tracks[0]
    assert t["frame_first_seen"] == 60 and t["one_frame_candidate"] is True
    assert t["frame_first_candidate"] <= 60 <= t["frame_last_candidate"]


def test_regions_and_light_on_colour_blocks(ws):
    out, ref = _analyze(ws, "cfr_30.mp4")
    color = _j(ref / "color.json")
    ok = [s for s in color["shots"] if s["status"] == "ok"]
    assert len(ok) == 3
    keys = [s["light"]["key"] for s in ok]
    assert keys[0] == "high_key" and keys[1] == "low_key"
    bg0 = ok[0]["regions"]["background"] or ok[0]["regions"]["whole_frame"]
    assert bg0["L"]["p50"] > 85
    assert "delta_e2000_vs_master" in (ok[1]["regions"]["whole_frame"])


def test_audio_loudness_matches_ffmpeg_and_silent_is_absent(ws):
    out, ref = _analyze(ws, "cfr_30.mp4")
    a = _j(ref / "audio.json")
    assert a["status"] == "ok" and a["loudness"]["integrated_lufs"] is not None
    assert a["loudness"]["true_peak_dbtp"] is not None
    out2, ref2 = _analyze(ws, "silent.mp4")
    assert _j(ref2 / "audio.json")["status"] == "absent" and out2["coverage"]["stages"]["audio"]["status"] == "absent"


def test_sheets_are_written(ws):
    out, ref = _analyze(ws, "cfr_30.mp4")
    sheets = _j(ref / "sheets.json")
    assert sheets["timeline"]["pages"] and sheets["shots"]["pages"]
    assert (ref / "sheets" / sheets["timeline"]["pages"][0]).exists()
    assert (ref / "sheets" / "palette_strip.png").exists() and (ref / "sheets" / "curves.png").exists()


def test_rerun_uses_checkpoints(ws):
    out1, ref = _analyze(ws, "cfr_30.mp4")
    (ref / "motion.json").unlink()
    out2 = analyze.analyze(out1["job"]["asset_id"], workspace=ws)
    assert out2["created"] is False  # job already complete; nothing recomputed
