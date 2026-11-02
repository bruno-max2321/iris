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
    from iris import audio

    out, ref = _analyze(ws, "cfr_30.mp4")
    a = _j(ref / "audio.json")
    assert a["status"] == "ok" and a["loudness"]["integrated_lufs"] is not None
    assert a["loudness"]["true_peak_dbtp"] is not None
    # the summary block, not the first gated progress line (-70.0): cross-check against loudnorm
    x = audio.loudness_crosscheck(FIX / "cfr_30.mp4")
    assert x["ok"]
    assert abs(a["loudness"]["integrated_lufs"] - x["integrated_lufs"]) <= 0.5
    assert abs(a["loudness"]["true_peak_dbtp"] - x["true_peak_dbtp"]) <= 0.5
    assert a["loudness"]["integrated_lufs"] > -60
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


def test_pick_frames_returns_exactly_the_requested_ids_without_select_expressions():
    from iris import decode

    ids = list(range(0, 90, 1)) + [89]
    arrays, err = decode.pick_frames(FIX / "cfr_30.mp4", ids, 96, 54)
    assert err is None and sorted(arrays) == list(range(90))
    arrays, err = decode.pick_frames(FIX / "cfr_30.mp4", [5, 400], 96, 54)
    assert 5 in arrays and 400 not in arrays and "1 of 2" in err


def test_analyze_force_recomputes_derived_stages(ws):
    out1, ref = _analyze(ws, "cfr_30.mp4")
    (ref / "shots.json").unlink()
    out2 = analyze.analyze(out1["job"]["asset_id"], workspace=ws)
    assert out2["created"] is False and out2["stages"]["shots"]["status"] == "ok"
    out3 = analyze.analyze(out1["job"]["asset_id"], workspace=ws, force=True)
    assert out3["created"] is True and (ref / "shots.json").exists()
    assert out3["stages"]["shots"].get("cached") is None


def test_worker_echo_and_stall_supervision(tmp_path):
    from iris import worker

    r = worker.run_worker("echo", {"n": 3, "sleep": 0.01}, first_budget_s=30, stall_budget_s=30, total_budget_s=60, workdir=tmp_path / "a")
    assert r["killed"] is None and r["result"]["status"] == "ok" and sum(1 for e in r["events"] if e["event"] == "tick") == 3
    r = worker.run_worker("echo", {"n": 2, "sleep": 0.01, "hang_after": 0}, first_budget_s=30, stall_budget_s=1.0, total_budget_s=60, workdir=tmp_path / "b")
    assert r["killed"] == "stall" and sum(1 for e in r["events"] if e["event"] == "tick") == 2


def test_ocr_dedup_marks_unchanged_samples(ws):
    from iris import textocr

    res = ingest.ingest(str(FIX / "caption_1frame.mp4"), "own", workspace=ws)
    m = res["manifest"]["probe"]["video"]
    out = ws / "x"; out.mkdir()
    ids = list(range(0, 90, 6))
    files, reuse_of, size, err = textocr.extract_frames(FIX / "caption_1frame.mp4", ids, out, 480, m["display_width"], m["display_height"])
    assert err is None and len(files) == len(ids) and size is not None
    # a static clip with one caption frame: most samples are visually identical to the previous key frame
    assert len(reuse_of) >= len(ids) // 2


def test_analyze_force_stages_subset_keeps_other_checkpoints(ws):
    out1, ref = _analyze(ws, "cfr_30.mp4")
    m_before = (ref / "motion.done.json").stat().st_mtime_ns
    out3 = analyze.analyze(out1["job"]["asset_id"], workspace=ws, force=True, stages=["audio"])
    assert out3["created"] is True
    assert (ref / "motion.done.json").stat().st_mtime_ns == m_before
    assert out3["stages"]["motion"].get("cached") is True and out3["stages"]["audio"].get("cached") is None


def test_tracks_merge_word_by_word_caption_growth():
    from iris import textocr

    W, H = 540, 960
    # a caption revealed in four steps on the middle band, box growing to the right; a second line below
    def box(x1, y):
        return [100, y, x1, y + 40]
    dets = {
        0: [{"text": "He", "conf": 0.99, "box": box(160, 500)}],
        6: [{"text": "He climbea", "conf": 0.92, "box": box(300, 500)}],
        12: [{"text": "He climbedonto", "conf": 0.90, "box": box(380, 500)}],
        18: [{"text": "Heclimbedontoa", "conf": 0.98, "box": box(420, 500)}],
        24: [{"text": "He climbed onto a", "conf": 0.97, "box": box(420, 500)},
             {"text": "hadamn", "conf": 0.97, "box": box(260, 560)}],
        30: [{"text": "He climbed onto a", "conf": 0.97, "box": box(420, 500)},
             {"text": "had a man", "conf": 0.95, "box": box(260, 560)}],
        42: [{"text": "cut the", "conf": 0.99, "box": box(240, 500)}],   # new caption after a gap: new track
    }
    tracks = textocr.build_tracks(dets, W, H, step=6, n_frames=60)
    texts = [t["text"] for t in tracks]
    assert texts == ["He climbed onto a", "had a man", "cut the"], texts
    first = tracks[0]
    assert first["reveal_steps"] == 3 and first["animation"] == "build_on"
    assert first["frame_first_seen"] == 0 and first["frame_last_seen"] == 30 and first["frame_full_text_seen"] == 18  # full content first read (unspaced) at 18
    assert tracks[1]["text"] == "had a man" and tracks[1]["reveal_steps"] == 0


def test_tracks_follow_a_caption_block_that_shifts_up_as_lines_are_added():
    from iris import textocr

    W, H = 540, 960
    def box(x0, x1, y):
        return [x0, y, x1, y + 40]
    # bottom-anchored block: line 1 moves up by one line height when line 2 appears, and again for line 3;
    # readings carry recogniser slips ("hadamn" / "hadamin" / "hadam:n")
    dets = {
        0: [{"text": "cut the", "conf": 0.99, "box": box(150, 300, 700)}],
        6: [{"text": "cut theon", "conf": 0.95, "box": box(150, 340, 650)}, {"text": "hadamn", "conf": 0.97, "box": box(160, 300, 700)}],
        12: [{"text": "cut theonly", "conf": 0.97, "box": box(150, 380, 600)}, {"text": "hadamin", "conf": 0.97, "box": box(160, 300, 650)}, {"text": "cable", "conf": 0.99, "box": box(170, 280, 700)}],
        18: [{"text": "cut the only", "conf": 0.97, "box": box(150, 380, 600)}, {"text": "hadam:n", "conf": 0.90, "box": box(160, 300, 650)}, {"text": "cable", "conf": 0.99, "box": box(170, 280, 700)}],
    }
    tracks = textocr.build_tracks(dets, W, H, step=6, n_frames=60)
    texts = sorted(t["text"] for t in tracks)
    assert texts == ["cable", "cut the only", "hadamn"], texts
    first = next(t for t in tracks if t["text"] == "cut the only")
    assert first["reveal_steps"] >= 2 and first["frame_first_seen"] == 0 and first["frame_last_seen"] == 18


def test_noisy_cut_frame_and_reflow_do_not_fragment_a_caption_block():
    from iris import textocr

    W, H = 540, 960
    def box(x0, x1, y):
        return [x0, y, x1, y + 40]
    block1 = [{"text": "He climbed onto a", "conf": 0.97, "box": box(120, 420, 600)}, {"text": "platform,", "conf": 0.96, "box": box(190, 350, 650)}]
    dets = {
        0: block1, 6: block1,
        9: [{"text": "Hc clmbd", "conf": 0.41, "box": box(100, 300, 610)}],          # blurred cut frame: garbage, other lines missed
        12: block1, 18: block1,
        24: [{"text": "hadamn", "conf": 0.97, "box": box(200, 340, 560)}, {"text": "cut theon", "conf": 0.95, "box": box(160, 380, 610)}],
        30: [{"text": "hadamou", "conf": 0.80, "box": box(200, 340, 560)}, {"text": "cut the only", "conf": 0.97, "box": box(150, 390, 610)},
             {"text": "cable", "conf": 0.99, "box": box(220, 320, 660)}],
        # block re-flows: every line jumps up by 0.33 of the frame when the next line arrives
        36: [{"text": "hadamn", "conf": 0.96, "box": box(200, 340, 240)}, {"text": "cut the only", "conf": 0.97, "box": box(150, 390, 290)},
             {"text": "cable", "conf": 0.99, "box": box(220, 320, 340)}, {"text": "holding him up,", "conf": 0.95, "box": box(130, 410, 390)}],
        42: [{"text": "hadamo", "conf": 0.90, "box": box(200, 340, 240)}, {"text": "cut the only", "conf": 0.97, "box": box(150, 390, 290)},
             {"text": "cable", "conf": 0.99, "box": box(220, 320, 340)}, {"text": "holding him up,", "conf": 0.95, "box": box(130, 410, 390)}],
    }
    dropped = []
    tracks = textocr.build_tracks(dets, W, H, step=6, n_frames=60, dropped_out=dropped)
    texts = sorted(t["text"] for t in tracks)
    assert texts == sorted(["He climbed onto a", "platform,", "hadamn", "cut the only", "cable", "holding him up,"]), texts
    assert [(d["text"], d["reason"]) for d in dropped] == [("Hc clmbd", "low_confidence")]
    by = {t["text"]: t for t in tracks}
    assert by["He climbed onto a"]["frame_first_seen"] == 0 and by["He climbed onto a"]["frame_last_seen"] == 18
    assert by["cable"]["frame_first_seen"] == 30 and by["cable"]["frame_last_seen"] == 42
    assert by["hadamn"]["frame_first_seen"] == 24 and by["hadamn"]["frame_last_seen"] == 42
    # blocks: lines that leave together are one cue
    assert by["He climbed onto a"]["block_id"] == by["platform,"]["block_id"]
    assert len({by[t]["block_id"] for t in ("hadamn", "cut the only", "cable", "holding him up,")}) == 1
    blocks = textocr.blocks_from_tracks(tracks)
    second = next(b for b in blocks if "cable" in b["text"])
    assert second["text"] == "hadamn cut the only cable holding him up," and second["lines"] == 4


def test_lines_far_apart_or_arriving_later_in_another_size_are_separate_blocks():
    from iris import textocr

    W, H = 540, 960
    def d(text, x0, x1, y, h=20):
        return {"text": text, "conf": 0.97, "box": [x0, y, x1, y + h]}
    small = [d("cut the only", 205, 285, 60), d("cable", 225, 270, 80)]          # earlier caption, shrunk in a picture-in-picture
    dets = {
        0: small, 6: small, 12: small + [d("and waited.", 225, 315, 315)],         # same size, far below: its own element
        18: small + [d("and waited.", 225, 315, 315), d("That 3 second moment", 98, 400, 600, h=50)],
        24: small + [d("and waited.", 225, 315, 315), d("That 3 second moment", 98, 400, 600, h=50)],
        # a caption whose bigger emphasis line arrives with it stays one block
        48: [d("nobody wants", 150, 390, 500, h=30), d("TO SOLVE", 120, 420, 535, h=70)],
        54: [d("nobody wants", 150, 390, 500, h=30), d("TO SOLVE", 120, 420, 535, h=70)],
        # a big line that arrives later right under a small one is a new element
        78: [d("Otis takes off", 219, 316, 523, h=33)],
        84: [d("Otis takes off", 219, 316, 523, h=33)],
        96: [d("Otis takes off", 219, 316, 523, h=33), d("All safe, gentlemen.", 64, 476, 560, h=70)],
        102: [d("Otis takes off", 219, 316, 523, h=33), d("All safe, gentlemen.", 64, 476, 560, h=70)],
    }
    tracks = textocr.build_tracks(dets, W, H, step=6, n_frames=110)
    texts = sorted(b["text"] for b in textocr.blocks_from_tracks(tracks))
    assert texts == sorted(["cut the only cable", "and waited.", "That 3 second moment", "nobody wants TO SOLVE", "Otis takes off",
                            "All safe, gentlemen."]), texts


def test_forced_recompute_that_fails_keeps_previous_output(ws, monkeypatch):
    out1, ref = _analyze(ws, "cfr_30.mp4")
    before = (ref / "audio.json").read_bytes()
    from iris import audio

    def boom(*a, **k):
        raise RuntimeError("simulated backend failure")
    monkeypatch.setattr(audio, "run", boom)
    out3 = analyze.analyze(out1["job"]["asset_id"], workspace=ws, force=True, stages=["audio"])
    rec = out3["stages"]["audio"]
    assert rec["status"] == "failed" and rec.get("kept_previous_output") is True
    assert (ref / "audio.json").read_bytes() == before


def test_junk_is_dropped_and_reveal_fragments_join_their_line():
    from iris import textocr

    W, H = 540, 960
    def d(text, x0, x1, y, conf=0.95):
        return {"text": text, "conf": conf, "box": [x0, y, x1, y + 40]}
    dets = {
        # first reveal caught mid-slide elsewhere, then the line settles
        228: [d("Elisha", 425, 540, 560), d("hasay", 433, 512, 610)],
        234: [d("Elisha Otis", 317, 510, 560), d("hasa problem", 323, 495, 610)],
        240: [d("Elisha Otis", 281, 472, 560), d("has a problem", 286, 454, 610)],
        246: [d("Elisha Otis", 263, 455, 560), d("has a problem", 269, 438, 610), d("8", 76, 140, 438, conf=0.8)],
        252: [d("Elisha Otis", 256, 449, 560), d("has a problem", 264, 431, 610), d("", 270, 290, 490, conf=0.0)],
        # one word split in two boxes; scene signage in another script; a stray digit
        372: [d("cal", 225, 281, 484), d("es", 288, 330, 484), d("萬兴镜", 317, 378, 272, conf=0.69), d("118", 397, 454, 779, conf=0.24)],
        378: [d("cales", 228, 333, 484), d("1852", 200, 340, 300)],
        384: [d("cales", 228, 333, 484), d("1852", 200, 340, 300)],
    }
    dropped = []
    tracks = textocr.build_tracks(dets, W, H, step=6, n_frames=400, dropped_out=dropped)
    texts = sorted(t["text"] for t in tracks)
    assert texts == ["1852", "Elisha Otis", "cales", "has a problem"], texts  # a held year card is text
    by = {t["text"]: t for t in tracks}
    assert by["has a problem"]["frame_first_seen"] == 228 and by["has a problem"].get("absorbed_fragments") == 1
    assert by["cales"]["frame_first_seen"] == 372
    assert {x["reason"] for x in dropped} == {"empty", "low_confidence", "other_script", "no_letters"}
    assert not any(t["text"] in ("8", "118", "") for t in tracks)
    assert [t["track_id"] for t in tracks] == [f"t{k:04d}" for k in range(len(tracks))]


def test_transcript_repairs_glued_words_and_is_idempotent():
    from iris import textocr

    doc = {"status": "ok",
           "tracks": [{"track_id": "t0000", "text": "He climbedontoa", "t_first_seen": 0.0, "t_last_seen": 1.5},
                      {"track_id": "t0001", "text": "PTBarmum", "t_first_seen": 31.25, "t_last_seen": 32.5},
                      {"track_id": "t0002", "text": "hadamn", "t_first_seen": 1.75, "t_last_seen": 2.5}],
           "blocks": [{"block_id": "b0000", "track_ids": ["t0000"], "text": "He climbedontoa", "words": 2}]}
    words = [{"w": w, "start": s} for w, s in [("He", 0.1), ("climbed", 0.3), ("onto", 0.6), ("a", 0.8), ("platform,", 1.0),
                                               ("So", 31.0), ("he", 31.2), ("writes", 31.4), ("to", 31.6), ("P.T.", 31.8), ("Barnum,", 32.0)]]
    rep = textocr.repair_with_transcript(doc, {"transcript": {"words": words}})
    t = {x["track_id"]: x for x in doc["tracks"]}
    assert t["t0000"]["text"] == "He climbed onto a" and t["t0000"]["text_ocr"] == "He climbedontoa" and t["t0000"]["text_source"] == "transcript"
    assert t["t0001"]["text"] == "P.T. Barnum,"
    assert t["t0002"]["text"] == "hadamn" and "text_ocr" not in t["t0002"]  # nothing spoken matches: OCR stays
    assert doc["blocks"][0]["words"] == 4 and rep["repaired_tracks"] == 2
    textocr.repair_with_transcript(doc, {"transcript": {"words": words}})
    assert t["t0000"]["text_ocr"] == "He climbedontoa" and t["t0000"]["text"] == "He climbed onto a"
    textocr.repair_with_transcript(doc, None)  # transcript gone: back to the OCR reading
    assert t["t0000"]["text"] == "He climbedontoa" and "text_source" not in t["t0000"]


def test_motion_on_twos_is_a_pan_and_a_glitch_is_not():
    import numpy as np

    from iris import motion

    w, fps = 192, 24.0
    still = {"dx": 0.0, "dy": 0.0, "div": 0.0, "mag": 0.0}
    step = {"dx": -2.0, "dy": 0.0, "div": 0.0, "mag": 2.0}
    sharp = np.full(25, 100.0)
    # animation on twos: the picture moves every other frame, so the median pair is still
    on_twos = [dict(step) if i % 2 else dict(still) for i in range(24)]
    assert motion.classify(on_twos, sharp, w, fps)["class"] == "pan_right"
    # a static shot with one glitched pair stays static
    glitch = [dict(still) for _ in range(24)]
    glitch[10] = {"dx": 40.0, "dy": -30.0, "div": 3.0, "mag": 50.0}
    assert motion.classify(glitch, sharp, w, fps)["class"] == "static"
    assert motion.event_pairs([{"type": "flash", "frame_first": 10, "length_frames": 1},
                               {"type": "freeze", "frame_first": 20, "length_frames": 30}]) == {10, 11}


def test_outputs_of_an_older_method_version_are_recomputed(ws, capsys):
    out, ref = _analyze(ws, "pan_right.mp4")
    a = out["job"]["asset_id"]
    m = _j(ref / "motion.json")
    m["method_version"] = "motion_phasecorr@0.0.1"
    (ref / "motion.json").write_text(json.dumps(m))
    text_before = (ref / "text.done.json").stat().st_mtime_ns
    out = analyze.analyze(a, workspace=ws)
    assert out["recomputed_stale_stages"] == ["motion"]
    from iris import motion
    assert _j(ref / "motion.json")["method_version"] == motion.METHOD_VERSION
    assert (ref / "text.done.json").stat().st_mtime_ns == text_before  # other checkpoints are kept
    assert "recomputed_stale_stages" not in analyze.analyze(a, workspace=ws)
    from iris.cli import main
    m["method_version"] = "motion_phasecorr@0.0.1"
    (ref / "motion.json").write_text(json.dumps(m))
    capsys.readouterr()
    assert main(["analyze", a]) == 0
    assert json.loads(capsys.readouterr().out)["recomputed_stale_stages"] == ["motion"]
