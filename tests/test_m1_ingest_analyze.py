"""Milestone 1 acceptance: every frame indexed and measured on valid fixtures, partial on corrupt ones,
idempotent ingest and analyze. Fixtures are generated on demand with tools/make_fixtures.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from iris import analyze, frames_io, ingest, paths

FIX = paths.FIXTURES_DIR / "synthetic"
MANIFEST = json.loads((paths.FIXTURES_DIR / "manifest.json").read_text(encoding="utf-8"))["fixtures"]


@pytest.fixture(scope="session", autouse=True)
def fixtures_present():
    if not (FIX / "cfr_30.mp4").exists():
        subprocess.run([str(paths.REPO_ROOT / "tools" / "make_fixtures.sh")], check=True, capture_output=True)
    assert (FIX / "cfr_30.mp4").exists()


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("IRIS_WORKSPACE", str(tmp_path))
    return tmp_path


def _run(ws: Path, name: str):
    res = ingest.ingest(str(FIX / name), "own", workspace=ws)
    out = analyze.analyze(res["asset_id"], workspace=ws)
    return res, out


def test_ingest_is_idempotent_on_content(ws):
    a = ingest.ingest(str(FIX / "cfr_30.mp4"), "own", workspace=ws)
    b = ingest.ingest(str(FIX / "cfr_30.mp4"), "own", workspace=ws)
    assert a["asset_id"].startswith("ref_") and a["created"] and not b["created"] and a["asset_id"] == b["asset_id"]
    m = a["manifest"]
    assert m["readable"] and m["probe"]["video"]["display_width"] == 1080 and m["probe"]["audio"] is not None


def test_cfr_all_frames_indexed_and_measured(ws):
    res, out = _run(ws, "cfr_30.mp4")
    cov = out["coverage"]
    assert cov["decode"] == "full" and cov["measurement"] == "full"
    assert cov["expected_frames"] == MANIFEST["cfr_30.mp4"]["frames"] == cov["measured_frames"]
    rows = frames_io.read_frames(ws / "refs" / res["asset_id"])
    assert len(rows) == 180
    # three colour blocks: coco (bright), charcoal (dark), accent (mid); cuts at frames 60 and 120
    assert rows[0]["L_mean"] > 85 and rows[70]["L_mean"] < 30
    diffs = [(r["frame_id"], r["hist_diff_prev"]) for r in rows if r["hist_diff_prev"] is not None]
    top = sorted(diffs, key=lambda x: -x[1])[:2]
    assert {f for f, _ in top} == {60, 120}
    assert out["job"]["state"] == "review_ready"


def test_analyze_is_idempotent(ws):
    res, out1 = _run(ws, "cfr_30.mp4")
    out2 = analyze.analyze(res["asset_id"], workspace=ws)
    assert out1["job"]["job_id"] == out2["job"]["job_id"] and out2["created"] is False


def test_vfr_time_is_not_frame_over_fps(ws):
    res, out = _run(ws, "vfr_mixed.mp4")
    assert out["coverage"]["decode"] == "full" and out["coverage"]["expected_frames"] == MANIFEST["vfr_mixed.mp4"]["frames"]
    idx = json.loads((ws / "refs" / res["asset_id"] / "index.json").read_text())
    assert idx["vfr"] is True
    nominal = idx["nominal_fps"]
    f = idx["frames"][100]
    assert abs(f["pts_time"] - f["frame_id"] / nominal) > 0.1


def test_one_frame_flash_survives(ws):
    res, out = _run(ws, "flash_1frame.mp4")
    rows = frames_io.read_frames(ws / "refs" / res["asset_id"])
    brightest = max(rows, key=lambda r: r["L_mean"])
    assert brightest["frame_id"] == 90 and brightest["L_mean"] > 80
    assert out["coverage"]["measured_frames"] == 180


def test_duplicate_frames_are_preserved(ws):
    res, out = _run(ws, "duplicate_frames.mp4")
    assert out["coverage"]["measured_frames"] == MANIFEST["duplicate_frames.mp4"]["frames"]
    rows = frames_io.read_frames(ws / "refs" / res["asset_id"])
    still = [r for r in rows if r["diff_prev"] is not None and r["diff_prev"] < 1e-4]
    assert len(still) >= 20


def _fixture_has_rotation(path: Path) -> bool:
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream_side_data=rotation:stream_tags=rotate", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return any(ch.isdigit() for ch in p.stdout)


def test_rotation_metadata_gives_portrait_display(ws):
    if not _fixture_has_rotation(FIX / "rotation_meta.mp4"):
        pytest.skip("this ffmpeg build did not write rotation metadata into the fixture; generator limitation, not an Iris defect")
    res = ingest.ingest(str(FIX / "rotation_meta.mp4"), "own", workspace=ws)
    v = res["manifest"]["probe"]["video"]
    assert v["rotation"] in (90, 270) and (v["display_width"], v["display_height"]) == (1080, 1920)
    out = analyze.analyze(res["asset_id"], workspace=ws)
    assert out["measure_summary"]["transform"]["analysis_height"] > out["measure_summary"]["transform"]["analysis_width"]


def test_silent_video_has_no_audio_but_analyzes(ws):
    res, out = _run(ws, "silent.mp4")
    assert res["manifest"]["probe"]["audio"] is None and out["coverage"]["decode"] == "full"


def test_truncated_is_partial_not_exception(ws):
    res, out = _run(ws, "truncated.mp4")
    cov = out["coverage"]
    assert cov["decode"] == "partial" and out["job"]["state"] == "partial" and cov["reasons"]


def test_source_hash_is_verified_on_resume(ws, tmp_path):
    copy = tmp_path / "copy.mp4"
    copy.write_bytes((FIX / "silent.mp4").read_bytes())
    res = ingest.ingest(str(copy), "own", workspace=ws)
    copy.write_bytes(b"corrupt" + copy.read_bytes())
    with pytest.raises(analyze.AnalyzeError) as exc:
        analyze.analyze(res["asset_id"], workspace=ws)
    assert exc.value.code == "validation"
