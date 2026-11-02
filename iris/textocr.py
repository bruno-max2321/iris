"""Stage F: on-screen text. Sampled OCR (economy: every 6th frame plus shot boundaries; strict: every
frame) with PaddleOCR mobile in a supervised child process when installed, Tesseract CLI as a fallback,
and an honest `skipped` status when neither exists. Detections are grouped into tracks; one-frame text
events are kept.

Speed and robustness levers, all reported in text.json:
- frames are extracted in one streaming decode pass (no ffmpeg `select` expression);
- visually unchanged samples reuse the previous key frame's detections (zone-max difference below a
  threshold; `frames_reused`), which typically halves the OCR work on caption-driven reels;
- PaddleOCR runs in its own interpreter with capped threads; a frame that stalls past its budget is
  recorded in `frames_timed_out`, the worker restarts on the next frame, and the stage still completes."""

from __future__ import annotations

import csv
import difflib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from . import decode, worker

METHOD_VERSION = "textocr@0.4.0"
OCR_LONG_SIDE = int(os.environ.get("IRIS_OCR_LONG_SIDE", "960"))
ECONOMY_STEP = 6
MISS_FRAMES_FACTOR = 2      # a track survives this many sampling steps without a matching detection
MIN_FREE_MATCH_CHARS = 4    # identical text this long continues a track wherever it moved
BLOCK_MAX_DY = 0.35         # lines of one caption block sit within this share of the frame height
CONF_MIN = 0.6              # tracks whose best reading is less confident than this are dropped
FRAGMENT_MAX_SPAN_STEPS = 1  # a track lasting at most this many steps that begins a track starting right after is its reveal
LINE_JOIN_GAP = 0.6         # boxes on one line closer than this share of the line height are one piece of text
MOVED_GROW_MIN_CHARS = 5    # a line that grows or is re-read while the block moves continues across one gap
FIRST_FRAME_BUDGET_S = float(os.environ.get("IRIS_OCR_FIRST_FRAME_BUDGET_S", "180"))   # model load + first frame
FRAME_BUDGET_S = float(os.environ.get("IRIS_OCR_FRAME_BUDGET_S", "20"))                 # stall budget per frame
MAX_RESTARTS = 3
DEDUP_THRESHOLD = float(os.environ.get("IRIS_OCR_DEDUP_THRESHOLD", "3.0"))              # zone-max mean abs diff, 0-255
DEDUP_ZONES = (4, 3)   # rows, cols


# ----------------------------------------------------------------------------------------------- backends
def available_backend() -> tuple[str | None, str | None]:
    """Decide the backend WITHOUT importing paddle in this process (its thread runtime stays in the child)."""
    if importlib.util.find_spec("paddleocr") is not None and importlib.util.find_spec("paddle") is not None:
        return "paddleocr-mobile", None
    if shutil.which("tesseract"):
        return "tesseract-cli", None
    return None, "paddleocr not installed; tesseract not found"


class _Tesseract:
    name = "tesseract-cli"

    def __init__(self) -> None:
        self.exe = shutil.which("tesseract")
        if not self.exe:
            raise RuntimeError("tesseract not found")
        self.lang = os.environ.get("IRIS_OCR_LANG_TESS", "eng")

    def detect(self, image_path: Path) -> list[dict[str, Any]]:
        p = subprocess.run([self.exe, str(image_path), "-", "--psm", "11", "-l", self.lang, "tsv"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if p.returncode != 0:
            return []
        rows = list(csv.DictReader(io.StringIO(p.stdout), delimiter="\t"))
        lines: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for r in rows:
            try:
                conf = float(r.get("conf", -1))
            except ValueError:
                continue
            text = (r.get("text") or "").strip()
            if conf < 50 or not text:
                continue
            key = (r["block_num"], r["par_num"], r["line_num"])
            lines.setdefault(key, []).append({"text": text, "conf": conf, "l": int(r["left"]), "t": int(r["top"]), "w": int(r["width"]), "h": int(r["height"])})
        out = []
        for words in lines.values():
            x0 = min(w["l"] for w in words); y0 = min(w["t"] for w in words)
            x1 = max(w["l"] + w["w"] for w in words); y1 = max(w["t"] + w["h"] for w in words)
            out.append({"text": " ".join(w["text"] for w in words), "conf": sum(w["conf"] for w in words) / len(words) / 100.0, "box": [x0, y0, x1, y1]})
        return out


# ----------------------------------------------------------------------------------------------- sampling
def sample_frame_ids(n_frames: int, shots: list[dict[str, Any]], mode: str) -> list[int]:
    if mode == "strict":
        return list(range(n_frames))
    ids = set(range(0, n_frames, ECONOMY_STEP))
    for s in shots:
        ids.add(s["frame_first"])
        ids.add(min(n_frames - 1, s["frame_first"] + 1))
        ids.add(s["frame_last_inclusive"])
    return sorted(i for i in ids if 0 <= i < n_frames)


def ocr_size(display_w: int, display_h: int, long_side: int) -> tuple[int, int]:
    if display_h >= display_w:
        h = long_side - (long_side % 2); w = int(round(display_w * h / display_h)); w -= w % 2
    else:
        w = long_side - (long_side % 2); h = int(round(display_h * w / display_w)); h -= h % 2
    return max(2, w), max(2, h)


def _thumb(rgb: np.ndarray) -> np.ndarray:
    """Coarse grayscale (about 16x16 cells per axis) used for the change test between samples."""
    g = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float32)
    h, w = g.shape
    bh, bw = max(1, h // 16), max(1, w // 16)
    return g[: (h // bh) * bh, : (w // bw) * bw].reshape(h // bh, bh, w // bw, bw).mean(axis=(1, 3))


def zone_max_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Largest mean absolute difference over a rows x cols grid of zones (0-255). A caption changing in one
    zone registers even when the rest of the frame is identical."""
    d = np.abs(a - b)
    rows, cols = DEDUP_ZONES
    h, w = d.shape
    bh, bw = max(1, h // rows), max(1, w // cols)
    zones = d[: (h // bh) * bh, : (w // bw) * bw].reshape(h // bh, bh, w // bw, bw).mean(axis=(1, 3))
    return float(zones.max())


def extract_frames(src: Path, frame_ids: list[int], out_dir: Path, long_side: int, display_w: int, display_h: int,
                   dedup: bool = True) -> tuple[dict[int, Path], dict[int, int], tuple[int, int] | None, str | None]:
    """Stream-decode once; write each sampled frame as JPEG; decide which frames need OCR.

    Returns (files, reuse_of, image_size, error). `reuse_of[fid] = key_fid` for frames visually unchanged
    versus the last key frame; those are not sent to the backend and inherit its detections."""
    from PIL import Image

    if not frame_ids:
        return {}, {}, None, None
    w, h = ocr_size(display_w, display_h, long_side)
    files: dict[int, Path] = {}
    reuse_of: dict[int, int] = {}
    last_key_fid: int | None = None
    last_thumb: np.ndarray | None = None
    size: tuple[int, int] | None = None
    try:
        for fid, rgb in decode.pick_frames_iter(src, frame_ids, w, h):
            f = out_dir / f"f_{fid:06d}.jpg"
            Image.fromarray(rgb).save(f, quality=92)
            files[fid] = f
            size = (rgb.shape[1], rgb.shape[0])
            if dedup:
                th = _thumb(rgb)
                if last_thumb is not None and last_key_fid is not None and zone_max_diff(th, last_thumb) < DEDUP_THRESHOLD:
                    reuse_of[fid] = last_key_fid
                else:
                    last_key_fid, last_thumb = fid, th
    except decode.DecodeError as exc:
        return files, reuse_of, size, f"decode failed: {exc}"
    missing = sorted(set(frame_ids) - files.keys())
    err = f"{len(missing)} of {len(frame_ids)} requested frames not reached (first missing {missing[0]})" if missing else None
    return files, reuse_of, size, err


# ----------------------------------------------------------------------------------------------- paddle run
def run_paddle(files: dict[int, Path], key_ids: list[int], workdir: Path) -> dict[str, Any]:
    """OCR the key frames in a supervised child; restart past a stalled frame; never raise."""
    by_path = {str(files[i]): i for i in key_ids}
    remaining = list(key_ids)
    detections: dict[int, list[dict[str, Any]]] = {}
    timings: list[float] = []
    timed_out: list[int] = []
    restarts = 0
    models = None
    init_s = None
    mkldnn = os.environ.get("IRIS_OCR_MKLDNN", "0") == "1"
    base = {"detections": detections, "timings": timings, "timed_out": timed_out, "models": models, "init_s": init_s, "mkldnn": mkldnn}
    while remaining:
        payload = {"images": [str(files[i]) for i in remaining], "lang": os.environ.get("IRIS_OCR_LANG", "en"),
                   "long_side": OCR_LONG_SIDE, "mkldnn": mkldnn}
        total = FIRST_FRAME_BUDGET_S + FRAME_BUDGET_S * len(remaining) + 60
        r = worker.run_worker("ocr", payload, first_budget_s=FIRST_FRAME_BUDGET_S, stall_budget_s=FRAME_BUDGET_S,
                              total_budget_s=total, workdir=workdir)
        done_here: set[int] = set()
        for ev in r["events"]:
            if ev.get("event") == "ready":
                base["models"], base["init_s"] = ev.get("models"), ev.get("init_s")
            elif ev.get("event") == "frame":
                fid = by_path.get(ev["image"])
                if fid is None:
                    continue
                detections[fid] = ev.get("dets", [])
                timings.append(float(ev.get("s", 0.0)))
                done_here.add(fid)
        remaining = [i for i in remaining if i not in done_here]
        base["restarts"] = restarts
        if r["killed"] == "stall" and remaining:
            offender = remaining.pop(0)
            timed_out.append(offender)
            restarts += 1
            base["restarts"] = restarts
            if restarts > MAX_RESTARTS:
                return {**base, "status": "failed",
                        "reason": f"paddleocr stalled on {len(timed_out)} frames (budget {FRAME_BUDGET_S:.0f} s each) after {MAX_RESTARTS} restarts; first stalled frame {timed_out[0]}"}
            continue
        if r["killed"] == "total":
            return {**base, "status": "failed", "reason": f"paddleocr exceeded the total budget of {total:.0f} s with {len(remaining)} frames left"}
        if r["exit"] not in (0, None) or (r["result"] or {}).get("status") != "ok":
            reason = (r["result"] or {}).get("reason") or (r["stderr_tail"].strip().splitlines() or ["worker exited"])[-1][:240]
            return {**base, "status": "failed", "reason": f"paddleocr worker failed: {reason}"}
        break
    return {**base, "status": "ok", "restarts": restarts}


# ----------------------------------------------------------------------------------------------- tracks
def _iou(a: list[float], b: list[float]) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _norm(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _containment(a: list[float], b: list[float]) -> float:
    """Intersection over the smaller box: a caption that grows word by word keeps containing its earlier self."""
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return inter / small if small > 0 else 0.0


def _near(prev_box: list[float], box: list[float]) -> bool:
    """Same caption line despite the block moving: captions anchored at the bottom or centre shift every
    earlier line up when a new line or word is added. Horizontal overlap >= 0.3 of the narrower box and
    a vertical centre distance <= 0.3 of the frame height count as the same place."""
    x0, x1 = max(prev_box[0], box[0]), min(prev_box[2], box[2])
    narrow = min(prev_box[2] - prev_box[0], box[2] - box[0])
    if narrow <= 0 or (x1 - x0) / narrow < 0.3:
        return False
    cy_prev = (prev_box[1] + prev_box[3]) / 2
    cy = (box[1] + box[3]) / 2
    return abs(cy - cy_prev) <= 0.3


def _match_score(tr: dict[str, Any], d_norm: str, nb: list[float]) -> tuple[float, str] | None:
    """Return (score, kind) when detection continues the track. kind: same | grow | shrink | similar | moved."""
    t_norm = tr["norm"]
    if not t_norm or not d_norm:
        return None
    if not _near(tr["box"], nb):
        if t_norm == d_norm and len(t_norm) >= MIN_FREE_MATCH_CHARS:
            return 1.8, "moved"             # block re-flowed: the same line jumped to another place
        return None
    iou = _iou(tr["box"], nb)
    if t_norm == d_norm:
        return 2.0 + iou, "same"
    if len(t_norm) >= 2 and d_norm.startswith(t_norm) and len(d_norm) > len(t_norm):
        return 1.5 + iou, "grow"            # build-on reveal: "he" -> "heclimbed"
    if len(d_norm) >= 2 and t_norm.startswith(d_norm) and len(d_norm) < len(t_norm):
        return 1.2 + iou, "shrink"          # reveal read with a dropped word, or the line exiting
    sim = difflib.SequenceMatcher(None, t_norm, d_norm).ratio()
    if sim >= 0.7:
        return sim + iou, "similar"         # recogniser slips: "hadamn" / "hadamin" / "hadam:n"; "climbea" -> "climbedonto"
    return None


def join_line_pieces(dets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Boxes on the same line that almost touch are one piece of text the detector split ("cal" + "es").
    Joined left to right, without a space when the gap is under a quarter of the line height."""
    items = sorted(dets, key=lambda d: (d["box"][1], d["box"][0]))
    out: list[dict[str, Any]] = []
    for d in sorted(items, key=lambda d: d["box"][0]):
        host = None
        for o in out:
            h = min(o["box"][3] - o["box"][1], d["box"][3] - d["box"][1])
            v = min(o["box"][3], d["box"][3]) - max(o["box"][1], d["box"][1])
            gap = d["box"][0] - o["box"][2]
            if h > 0 and v >= 0.6 * h and -0.2 * h <= gap <= LINE_JOIN_GAP * h and _norm(o["text"]) and _norm(d["text"]):
                host = (o, gap, h)
                break
        if host is None:
            out.append({"text": d["text"], "conf": d["conf"], "box": list(d["box"])})
            continue
        o, gap, h = host
        o["text"] = o["text"] + ("" if gap < 0.25 * h else " ") + d["text"]
        o["conf"] = min(o["conf"], d["conf"])
        o["box"] = [min(o["box"][0], d["box"][0]), min(o["box"][1], d["box"][1]), max(o["box"][2], d["box"][2]), max(o["box"][3], d["box"][3])]
    return out


def build_tracks(detections: dict[int, list[dict[str, Any]]], img_w: int, img_h: int, step: int, n_frames: int,
                 lang: str = "en", dropped_out: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Group per-frame detections into text tracks, one per caption line. A line revealed word by word is one
    track (growth steps counted in `reveal_steps`). Robust to the failure modes of short-form video:

    - a sampled frame that misreads or drops a line (cut frames, motion blur, flashes) does not end the
      track: a track survives up to MISS_FRAMES_FACTOR * step frames without a matching detection;
    - detections are assigned to tracks globally, best score first, so an early track cannot steal the
      detection that belongs to a later one;
    - identical text (>= MIN_FREE_MATCH_CHARS characters) continues a track even when the block re-flows
      and the line jumps elsewhere;
    - after tracking, temporally adjacent tracks with the same or similar text in the same place merge, and
      across one gap a line that grew or was re-read while the block moved continues;
    - boxes the detector split on one line are joined before tracking;
    - a short fragment that begins a track starting right after, or duplicates a line inside its span,
      is absorbed by it;
    - finished tracks with nothing worth keeping (see drop_reason) are left out and reported in `dropped_out`.

    Lines that are on screen together and leave together form a block (`block_id`): one caption cue."""
    tracks: list[dict[str, Any]] = []
    open_tracks: list[dict[str, Any]] = []
    gap = MISS_FRAMES_FACTOR * step
    for fid in sorted(detections):
        alive = []
        for tr in open_tracks:
            (alive if fid - tr["last_sampled_frame"] <= gap else tracks).append(tr)
        open_tracks = alive
        dets = join_line_pieces(detections[fid])
        norm_dets = [(_norm(d["text"]), [d["box"][0] / img_w, d["box"][1] / img_h, d["box"][2] / img_w, d["box"][3] / img_h]) for d in dets]
        pairs = []
        for ti, tr in enumerate(open_tracks):
            for i in range(len(dets)):
                res = _match_score(tr, norm_dets[i][0], norm_dets[i][1])
                if res:
                    pairs.append((res[0], ti, i, res[1]))
        pairs.sort(key=lambda p: (-p[0], p[1], p[2]))
        used_t: set[int] = set()
        matched: set[int] = set()
        for _score, ti, i, kind in pairs:
            if ti in used_t or i in matched:
                continue
            used_t.add(ti)
            matched.add(i)
            tr, d = open_tracks[ti], dets[i]
            d_norm, nb = norm_dets[i]
            tr["last_sampled_frame"] = fid
            tr["samples"].append(fid)
            tr["readings"].append((d["text"], d["conf"], d_norm, fid))
            if kind == "grow" or (kind == "similar" and len(d_norm) > len(tr["norm"]) + 1):
                # growth, including growth read with a recogniser slip ("climbea" -> "climbed onto")
                tr["reveal_steps"] += 1
                tr["norm"], tr["box"] = d_norm, nb
            elif kind == "moved":
                tr["box"] = nb
            elif kind in ("same", "similar"):
                tr["box"] = [(x + y) / 2 for x, y in zip(tr["box"], nb)]
            if d["conf"] > tr["conf"]:
                tr["conf"] = d["conf"]
        for i, d in enumerate(dets):
            if i in matched:
                continue
            d_norm, nb = norm_dets[i]
            open_tracks.append({"norm": d_norm, "conf": d["conf"], "box": nb, "first_sampled_frame": fid,
                                "last_sampled_frame": fid, "samples": [fid], "reveal_steps": 0,
                                "readings": [(d["text"], d["conf"], d_norm, fid)]})
    tracks.extend(open_tracks)
    tracks = _merge_adjacent(sorted(tracks, key=lambda t: (t["first_sampled_frame"], t["box"][1])), gap)
    tracks = _absorb_fragments(tracks, step)
    out = []
    for k, tr in enumerate(tracks):
        # final text: majority vote over normalised readings that are at least 80% as long as the longest
        # (slips like "hadamin" lose to the repeated "hadamn"; partial reveals lose to the full line),
        # then the longest, the one with most spaces, the most confident
        longest = max(len(r[2]) for r in tr["readings"])
        finals = [r for r in tr["readings"] if len(r[2]) >= 0.8 * longest]
        counts: dict[str, int] = {}
        for r in finals:
            counts[r[2]] = counts.get(r[2], 0) + 1
        text, conf, _, t_full = max(finals, key=lambda r: (counts[r[2]], len(r[2]), r[0].count(" "), r[1]))
        t_full = min(r[3] for r in finals if r[2] == _norm(text))
        cy = (tr["box"][1] + tr["box"][3]) / 2
        zone = "upper_third" if cy < 1 / 3 else ("middle_band" if cy < 2 / 3 else "lower_third")
        rel_h = tr["box"][3] - tr["box"][1]
        width = tr["box"][2] - tr["box"][0]
        klass = "subtitle_candidate" if (zone != "upper_third" and width > 0.25 and rel_h < 0.12) else "text"
        out.append({
            "track_id": f"t{k:04d}", "text": text, "conf": round(conf, 3),
            "box_norm": [round(v, 4) for v in tr["box"]], "zone": zone, "rel_height": round(rel_h, 4),
            "frame_first_seen": tr["first_sampled_frame"], "frame_last_seen": tr["last_sampled_frame"],
            "frame_full_text_seen": t_full,
            # candidate span: the text may have appeared up to (step-1) frames before the first sample
            "frame_first_candidate": max(0, tr["first_sampled_frame"] - (step - 1)),
            "frame_last_candidate": min(n_frames - 1, tr["last_sampled_frame"] + (step - 1)),
            "samples": len(tr["samples"]), "class": klass,
            "reveal_steps": tr["reveal_steps"],
            "animation": "build_on" if tr["reveal_steps"] >= 2 else ("step" if tr["reveal_steps"] == 1 else "static_or_cut"),
            "readings": len(tr["readings"]),
            "one_frame_candidate": len(tr["samples"]) == 1,
            **({"absorbed_fragments": tr["absorbed"]} if tr.get("absorbed") else {}),
        })
    kept, dropped = [], []
    for t in out:
        reason = drop_reason(t, lang)
        if reason:
            dropped.append({"text": t["text"], "conf": t["conf"], "frame_first_seen": t["frame_first_seen"], "frame_last_seen": t["frame_last_seen"], "reason": reason})
        else:
            kept.append(t)
    for k, t in enumerate(kept):
        t["track_id"] = f"t{k:04d}"
    _assign_blocks(kept, step)
    if dropped_out is not None:
        dropped_out.extend(dropped)
    return kept


def _merge_adjacent(tracks: list[dict[str, Any]], gap: int) -> list[dict[str, Any]]:
    """Join track B into track A when B starts after A ends, within `gap` frames, with the same, grown or
    similar text, in the same place (or anywhere for identical long text)."""
    merged: list[dict[str, Any]] = []
    for tr in tracks:
        host = None
        for cand in reversed(merged):
            dt = tr["first_sampled_frame"] - cand["last_sampled_frame"]
            if dt <= 0 or dt > gap:
                continue
            if (_match_score(cand, tr["norm"], tr["box"]) or any(_match_score(cand, r[2], tr["box"]) for r in tr["readings"][:3])
                    or any(_moved_continuation(cand["norm"], n) for n in [tr["norm"]] + [r[2] for r in tr["readings"][:3]])):
                host = cand
                break
        if host is None:
            merged.append(tr)
            continue
        if tr["norm"].startswith(host["norm"]) and len(tr["norm"]) > len(host["norm"]):
            host["reveal_steps"] += 1
            host["norm"] = tr["norm"]
        host["reveal_steps"] += tr["reveal_steps"]
        host["samples"] += tr["samples"]
        host["readings"] += tr["readings"]
        host["last_sampled_frame"] = tr["last_sampled_frame"]
        host["box"] = tr["box"]
        host["conf"] = max(host["conf"], tr["conf"])
    return merged


def _moved_continuation(a: str, b: str) -> bool:
    """b continues a after the caption block moved: the same line grown ("cuttheon" -> "cuttheonly") or
    re-read with a slip ("hadamn" -> "hadamo"). Only used across a gap, never inside one sampled frame."""
    if len(a) < MOVED_GROW_MIN_CHARS or len(b) < MOVED_GROW_MIN_CHARS:
        return False
    if b.startswith(a) or a.startswith(b):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def _begins(fragment: str, text: str) -> bool:
    """The fragment is the first reveal of `text`, read with at most a slip ("hasay" / "hasaproblem",
    "newk" / "newyorks", "cotissteps" / "otisstepsonto", "theyre" / "theyveexisted")."""
    if not fragment or not text or len(fragment) >= len(text) + 2:
        return False
    if text.startswith(fragment) or (len(fragment) >= 4 and fragment[1:] in text[: len(fragment) + 1]):
        return True
    return len(fragment) >= 3 and difflib.SequenceMatcher(None, fragment, text[: len(fragment)]).ratio() >= 0.75


def _absorb_fragments(tracks: list[dict[str, Any]], step: int) -> list[dict[str, Any]]:
    """A track lasting at most FRAGMENT_MAX_SPAN_STEPS steps is absorbed by a longer track when
    - its text begins the longer track, which starts within two steps after it: the first reveal, often
      caught mid-slide in another place ("hasay" before "has a problem");
    - or it lies inside the longer track's span and reads like it: a duplicate misreading of the same line
      in a frame where the box split ("Ine crowd" under "The crowd screams.", "Withtin-decades").
    It extends the host's span instead of standing as a cue of its own."""
    out = []
    for f in tracks:
        host = None
        if f["last_sampled_frame"] - f["first_sampled_frame"] <= FRAGMENT_MAX_SPAN_STEPS * step:
            for h in tracks:
                if h is f or h["last_sampled_frame"] - h["first_sampled_frame"] <= f["last_sampled_frame"] - f["first_sampled_frame"]:
                    continue
                norms = [h["norm"]] + [r[2] for r in h["readings"][:3]]
                starts_after = f["first_sampled_frame"] <= h["first_sampled_frame"] <= f["last_sampled_frame"] + 2 * step
                inside = h["first_sampled_frame"] - step <= f["first_sampled_frame"] and f["last_sampled_frame"] <= h["last_sampled_frame"] + step
                if (starts_after or inside) and any(_begins(f["norm"], n) for n in norms):
                    host = h
                    break
                if inside and difflib.SequenceMatcher(None, f["norm"], h["norm"]).ratio() >= 0.75:
                    host = h
                    break
        if host is None:
            out.append(f)
            continue
        host["first_sampled_frame"] = min(host["first_sampled_frame"], f["first_sampled_frame"])
        host["samples"] = sorted(set(host["samples"]) | set(f["samples"]))
        host["reveal_steps"] += 1
        host["absorbed"] = host.get("absorbed", 0) + 1
    return out


def drop_reason(track: dict[str, Any], lang: str = "en") -> str | None:
    """Why a finished track is not text worth keeping: nothing read, unconfident, no letters (stray digits
    on a cut frame), a script other than the video's language (scene signage), or a lone character."""
    norm = _norm(track["text"])
    if not norm:
        return "empty"
    if track["conf"] < CONF_MIN:
        return "low_confidence"
    letters = [ch for ch in track["text"] if ch.isalpha()]
    if not letters:
        return "no_letters"
    if lang.startswith("en") and not any(ch.isascii() for ch in letters):
        return "other_script"
    if len(norm) == 1 and track["samples"] <= 1:
        return "single_character"
    return None


def _assign_blocks(tracks: list[dict[str, Any]], step: int) -> None:
    """Lines on screen at the same time, stacked in the same column, that leave within one sample of each
    other belong to one caption block (one cue). Sets `block_id` on every track."""
    n = len(tracks)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        a = tracks[i]
        for j in range(i + 1, n):
            b = tracks[j]
            if a["frame_first_seen"] > b["frame_last_seen"] or b["frame_first_seen"] > a["frame_last_seen"]:
                continue
            if abs(a["frame_last_seen"] - b["frame_last_seen"]) > step:
                continue
            ba, bb = a["box_norm"], b["box_norm"]
            if abs((ba[1] + ba[3]) / 2 - (bb[1] + bb[3]) / 2) > BLOCK_MAX_DY or min(ba[2], bb[2]) - max(ba[0], bb[0]) <= 0:
                continue
            parent[find(j)] = find(i)
    roots: dict[int, str] = {}
    for i, t in enumerate(tracks):
        r = find(i)
        roots.setdefault(r, f"b{len(roots):04d}")
        t["block_id"] = roots[r]


def blocks_from_tracks(tracks: list[dict[str, Any]], pts: dict[int, Any] | None = None) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for t in tracks:
        groups.setdefault(t.get("block_id") or t["track_id"], []).append(t)
    out = []
    for bid, lines in groups.items():
        lines = sorted(lines, key=lambda t: (t["box_norm"][1] + t["box_norm"][3]) / 2)
        f0 = min(t["frame_first_seen"] for t in lines)
        f1 = max(t["frame_last_seen"] for t in lines)
        cy = sum((t["box_norm"][1] + t["box_norm"][3]) / 2 for t in lines) / len(lines)
        text = " ".join(t["text"] for t in lines)
        out.append({"block_id": bid, "track_ids": [t["track_id"] for t in lines], "text": text, "lines": len(lines),
                    "words": len(text.split()), "frame_first_seen": f0, "frame_last_seen": f1,
                    "t_first_seen": (pts or {}).get(f0), "t_last_seen": (pts or {}).get(f1),
                    "zone": "upper_third" if cy < 1 / 3 else ("middle_band" if cy < 2 / 3 else "lower_third"),
                    "caption_like": any(t.get("class") == "subtitle_candidate" or t.get("zone") != "upper_third" for t in lines)})
    return sorted(out, key=lambda b: (b["frame_first_seen"], b["block_id"]))


# ----------------------------------------------------------------------------------------- transcript
REPAIR_MIN_RATIO = 0.8      # OCR letters vs the spoken words' letters
REPAIR_WINDOW_S = 2.0       # spoken words this far around the caption's span may be its source


def _plain_word(w: str) -> str:
    return w.strip().strip("\"“”«»()[]")


def repair_with_transcript(text_doc: dict[str, Any], audio_doc: dict[str, Any] | None) -> dict[str, Any]:
    """Caption lines in short-form video usually spell the voice-over. The OCR of tight display fonts drops
    spaces and slips letters ("He climbedontoa", "PTBarmum"), which breaks words-per-cue and caption-to-speech
    alignment. For each track, the run of spoken words near its span whose letters best match the OCR letters
    replaces the text when the match is close (ratio >= REPAIR_MIN_RATIO, length within 20%); the OCR reading
    is kept in `text_ocr` and `text_source` says "transcript". Idempotent: it always starts from `text_ocr`.
    Without a transcript every track keeps its OCR text."""
    tracks = text_doc.get("tracks") or []
    words = (((audio_doc or {}).get("transcript") or {}).get("words")) or []
    spoken = [(_plain_word(w.get("w", "")), _norm(w.get("w", "")), float(w["start"])) for w in words
              if w.get("start") is not None and _norm(w.get("w", ""))]
    repaired = 0
    for t in tracks:
        ocr = t.pop("text_ocr", None) or t["text"]
        t.pop("text_source", None)
        t["text"] = ocr
        target = _norm(ocr)
        if not spoken or len(target) < 4 or t.get("t_first_seen") is None:
            continue
        lo = float(t["t_first_seen"]) - REPAIR_WINDOW_S
        hi = float(t.get("t_last_seen") if t.get("t_last_seen") is not None else t["t_first_seen"]) + REPAIR_WINDOW_S
        best = None
        for a in range(len(spoken)):
            if not lo <= spoken[a][2] <= hi:
                continue
            cat = ""
            for b in range(a, len(spoken)):
                if spoken[b][2] > hi:
                    break
                cat += spoken[b][1]
                if len(cat) > len(target) + 3:
                    break
                r = difflib.SequenceMatcher(None, target, cat).ratio()
                if best is None or r > best[0]:
                    best = (r, a, b, len(cat))
        if best is None or best[0] < REPAIR_MIN_RATIO or abs(best[3] - len(target)) > max(2, 0.2 * len(target)):
            continue
        new = " ".join(spoken[i][0] for i in range(best[1], best[2] + 1) if spoken[i][0])
        tail = ocr.rstrip()[-1:] if ocr.rstrip()[-1:] in ".,!?;:" else ""
        if tail and new[-1:] not in ".,!?;:":
            new += tail
        if ocr[:1].isupper() and new[:1].islower() and ocr[:1].lower() == new[:1]:
            new = new[:1].upper() + new[1:]
        if new != ocr:
            t["text_ocr"], t["text"], t["text_source"] = ocr, new, "transcript"
            repaired += 1
    by_id = {t["track_id"]: t for t in tracks}
    for b in text_doc.get("blocks") or []:
        lines = [by_id[i] for i in b.get("track_ids") or [] if i in by_id]
        if lines:
            b["text"] = " ".join(t["text"] for t in lines)
            b["words"] = len(b["text"].split())
    text_doc["transcript_repair"] = {"repaired_tracks": repaired, "tracks": len(tracks), "transcript_words": len(spoken),
                                     "min_ratio": REPAIR_MIN_RATIO, "window_s": REPAIR_WINDOW_S}
    return text_doc["transcript_repair"]


# ----------------------------------------------------------------------------------------------- stage
def run(src: Path, ref_dir: Path, shots: list[dict[str, Any]], n_frames: int, display_w: int, display_h: int,
        index_frames: list[dict[str, Any]], mode: str = "economy") -> dict[str, Any]:
    base = {"schema_version": "1.0.0", "method_version": METHOD_VERSION}
    backend, err = available_backend()
    if backend is None:
        return {**base, "status": "skipped", "reason": err, "sampled_frames": 0, "tracks": []}
    step = 1 if mode == "strict" else ECONOMY_STEP
    ids = sample_frame_ids(n_frames, shots, mode)
    tmp = Path(tempfile.mkdtemp(prefix="iris-ocr-", dir=str(ref_dir)))
    timing: dict[str, Any] = {}
    try:
        t0 = time.time()
        files, reuse_of, size, extract_err = extract_frames(src, ids, tmp, OCR_LONG_SIDE, display_w, display_h,
                                                            dedup=os.environ.get("IRIS_OCR_DEDUP", "1") == "1")
        timing["extract_s"] = round(time.time() - t0, 3)
        if len(files) != len(ids):
            return {**base, "status": "failed", "backend": backend, "sampled_frames": len(ids), "tracks": [],
                    "reason": f"frame extraction returned {len(files)} of {len(ids)} frames: {extract_err or 'unknown'}"}
        key_ids = [i for i in ids if i not in reuse_of]
        t0 = time.time()
        if backend == "paddleocr-mobile":
            res = run_paddle(files, key_ids, tmp)
        else:
            tess = _Tesseract()
            res = {"status": "ok", "detections": {}, "timings": [], "timed_out": [], "models": f"tesseract {tess.lang}", "restarts": 0, "init_s": 0.0}
            for fid in key_ids:
                t1 = time.time()
                res["detections"][fid] = tess.detect(files[fid])
                res["timings"].append(time.time() - t1)
        timing["ocr_s"] = round(time.time() - t0, 3)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    detections: dict[int, list[dict[str, Any]]] = {}
    for fid in ids:
        dets = res["detections"].get(reuse_of.get(fid, fid))
        if dets:
            detections[fid] = dets
    img_w, img_h = size or (1, 1)
    dropped: list[dict[str, Any]] = []
    lang = os.environ.get("IRIS_OCR_LANG", "en")
    tracks = build_tracks(detections, img_w, img_h, step, n_frames, lang=lang, dropped_out=dropped) if detections else []
    pts = {f["frame_id"]: f.get("pts_time") for f in index_frames}
    for tr in tracks:
        tr["t_first_seen"] = pts.get(tr["frame_first_seen"])
        tr["t_last_seen"] = pts.get(tr["frame_last_seen"])
    blocks = blocks_from_tracks(tracks, pts)
    # raw detections, so the tracker can be retuned without running OCR again
    raw = {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "image_size": [size[0], size[1]] if size else None, "step": step,
           "detections": {str(f): [[d["text"], round(float(d["conf"]), 3), *[int(round(v)) for v in d["box"]]] for d in v] for f, v in sorted(detections.items())}}
    (ref_dir / "text_detections.json").write_text(json.dumps(raw, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    timings = res.get("timings") or []
    reason = res.get("reason")
    if res["status"] == "ok" and res.get("timed_out"):
        reason = f"{len(res['timed_out'])} frames exceeded the per-frame budget and were skipped"
    return {
        **base, "status": res["status"], "reason": reason,
        "backend": backend, "models": res.get("models"), "lang": lang,
        "mode": mode, "step": step, "long_side": OCR_LONG_SIDE,
        "sampled_frames": len(ids), "frames_ocr": len(key_ids), "frames_reused": len(reuse_of),
        "frames_timed_out": res.get("timed_out", []), "worker_restarts": res.get("restarts", 0),
        "seconds_per_frame": round(sum(timings) / len(timings), 3) if timings else None,
        "timing": {**timing, "model_init_s": res.get("init_s")},
        "frames_with_text": len(detections), "detections": sum(len(v) for v in detections.values()),
        "image_size": [img_w, img_h], "tracks": tracks, "blocks": blocks, "dropped": dropped,
        "caption_blocks": sum(1 for b in blocks if b["caption_like"]),
        "cue_timing_uncertainty_frames": step - 1, "dedup_threshold": DEDUP_THRESHOLD,
    }
