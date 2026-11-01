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
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from . import decode, worker

METHOD_VERSION = "textocr@0.2.1"
OCR_LONG_SIDE = int(os.environ.get("IRIS_OCR_LONG_SIDE", "960"))
ECONOMY_STEP = 6
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
        p = subprocess.run([self.exe, str(image_path), "-", "--psm", "11", "-l", self.lang, "tsv"], capture_output=True, text=True, timeout=120)
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


def _same_line(prev_box: list[float], box: list[float]) -> bool:
    """Vertical overlap of the two boxes relative to the shorter one (text lines keep their baseline)."""
    top, bottom = max(prev_box[1], box[1]), min(prev_box[3], box[3])
    h = min(prev_box[3] - prev_box[1], box[3] - box[1])
    return h > 0 and (bottom - top) / h >= 0.5


def _match_score(tr: dict[str, Any], d_norm: str, nb: list[float]) -> tuple[float, str] | None:
    """Return (score, kind) when detection continues the track. kind: same | grow | shrink | similar."""
    t_norm = tr["norm"]
    if not t_norm or not d_norm:
        return None
    if _iou(tr["box"], nb) >= 0.4 and t_norm == d_norm:
        return 2.0 + _iou(tr["box"], nb), "same"
    if _same_line(tr["box"], nb) and _containment(tr["box"], nb) >= 0.6:
        if len(t_norm) >= 2 and d_norm.startswith(t_norm) and len(d_norm) > len(t_norm):
            return 1.5 + _containment(tr["box"], nb), "grow"        # build-on reveal: "He" -> "He climbed"
        if len(d_norm) >= 2 and t_norm.startswith(d_norm) and len(d_norm) < len(t_norm):
            return 1.2 + _containment(tr["box"], nb), "shrink"      # reveal read with a dropped word, or exit
    sim = difflib.SequenceMatcher(None, t_norm, d_norm).ratio()
    if _iou(tr["box"], nb) >= 0.4 and sim >= 0.6:
        return _iou(tr["box"], nb) + sim, "similar"
    return None


def build_tracks(detections: dict[int, list[dict[str, Any]]], img_w: int, img_h: int, step: int, n_frames: int) -> list[dict[str, Any]]:
    """Group per-frame detections into text tracks. A caption revealed word by word (the dominant short-form
    style) is one track: its growth steps are counted in `reveal_steps` and its final text is the longest
    reading, preferring the variant with the most spaces (recognisers often merge italic words)."""
    tracks: list[dict[str, Any]] = []
    open_tracks: list[dict[str, Any]] = []
    for fid in sorted(detections):
        dets = detections[fid]
        norm_dets = [(_norm(d["text"]), [d["box"][0] / img_w, d["box"][1] / img_h, d["box"][2] / img_w, d["box"][3] / img_h]) for d in dets]
        matched: set[int] = set()
        still_open = []
        for tr in open_tracks:
            best, best_i, best_kind = None, -1, ""
            for i, d in enumerate(dets):
                if i in matched:
                    continue
                res = _match_score(tr, norm_dets[i][0], norm_dets[i][1])
                if res and (best is None or res[0] > best):
                    best, best_i, best_kind = res[0], i, res[1]
            if best_i >= 0 and fid - tr["last_sampled_frame"] <= step * 2:
                d = dets[best_i]
                d_norm, nb = norm_dets[best_i]
                matched.add(best_i)
                tr["last_sampled_frame"] = fid
                tr["samples"].append(fid)
                tr["readings"].append((d["text"], d["conf"], d_norm, fid))
                if best_kind == "grow" or (best_kind == "similar" and len(d_norm) > len(tr["norm"]) + 1):
                    # growth, including growth read with a recogniser slip ("climbea" -> "climbed onto")
                    tr["reveal_steps"] += 1
                    tr["norm"], tr["box"] = d_norm, nb
                elif best_kind in ("same", "similar"):
                    tr["box"] = [(x + y) / 2 for x, y in zip(tr["box"], nb)]
                    if d["conf"] > tr["conf"]:
                        tr["conf"] = d["conf"]
                still_open.append(tr)
            else:
                tracks.append(tr)
        open_tracks = still_open
        for i, d in enumerate(dets):
            if i in matched:
                continue
            d_norm, nb = norm_dets[i]
            open_tracks.append({"norm": d_norm, "conf": d["conf"], "box": nb, "first_sampled_frame": fid,
                                "last_sampled_frame": fid, "samples": [fid], "reveal_steps": 0,
                                "readings": [(d["text"], d["conf"], d_norm, fid)]})
    tracks.extend(open_tracks)
    out = []
    for k, tr in enumerate(tracks):
        # final text: among readings of the longest normalised content, most spaces first, then confidence
        longest = max(len(r[2]) for r in tr["readings"])
        finals = [r for r in tr["readings"] if len(r[2]) == longest]
        text, conf, _, t_full = max(finals, key=lambda r: (r[0].count(" "), r[1]))
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
        })
    return out


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
    tracks = build_tracks(detections, img_w, img_h, step, n_frames) if detections else []
    pts = {f["frame_id"]: f.get("pts_time") for f in index_frames}
    for tr in tracks:
        tr["t_first_seen"] = pts.get(tr["frame_first_seen"])
        tr["t_last_seen"] = pts.get(tr["frame_last_seen"])
    timings = res.get("timings") or []
    reason = res.get("reason")
    if res["status"] == "ok" and res.get("timed_out"):
        reason = f"{len(res['timed_out'])} frames exceeded the per-frame budget and were skipped"
    return {
        **base, "status": res["status"], "reason": reason,
        "backend": backend, "models": res.get("models"), "lang": os.environ.get("IRIS_OCR_LANG", "en"),
        "mode": mode, "step": step, "long_side": OCR_LONG_SIDE,
        "sampled_frames": len(ids), "frames_ocr": len(key_ids), "frames_reused": len(reuse_of),
        "frames_timed_out": res.get("timed_out", []), "worker_restarts": res.get("restarts", 0),
        "seconds_per_frame": round(sum(timings) / len(timings), 3) if timings else None,
        "timing": {**timing, "model_init_s": res.get("init_s")},
        "frames_with_text": len(detections), "detections": sum(len(v) for v in detections.values()),
        "image_size": [img_w, img_h], "tracks": tracks,
        "cue_timing_uncertainty_frames": step - 1, "dedup_threshold": DEDUP_THRESHOLD,
    }
