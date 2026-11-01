"""Stage F: on-screen text. Sampled OCR (economy: every 6th frame plus shot boundaries; strict: every
frame) with PaddleOCR mobile when installed, Tesseract CLI as a fallback, and an honest `skipped`
status when neither exists. Detections are grouped into tracks; one-frame text events are kept."""

from __future__ import annotations

import csv
import difflib
import io
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

METHOD_VERSION = "textocr@0.1.2"
OCR_LONG_SIDE = 960
ECONOMY_STEP = 6
FIRST_FRAME_BUDGET_S = float(os.environ.get("IRIS_OCR_FIRST_FRAME_BUDGET_S", "30"))
FRAME_BUDGET_S = float(os.environ.get("IRIS_OCR_FRAME_BUDGET_S", "5"))


# ----------------------------------------------------------------------------------------------- backends
class _Paddle:
    name = "paddleocr-mobile"

    def __init__(self) -> None:
        from paddleocr import PaddleOCR  # type: ignore

        lang = os.environ.get("IRIS_OCR_LANG", "en")
        # Document orientation and UVDoc unwarping are on by default in PaddleOCR 3.x and take minutes per
        # image on a CPU without oneDNN. Video frames are never warped documents, so both stay off.
        kwargs = dict(
            lang=lang, device="cpu", enable_mkldnn=False, cpu_threads=min(4, os.cpu_count() or 1),
            text_det_limit_side_len=OCR_LONG_SIDE, text_det_limit_type="max",
            use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
        )
        try:
            self.ocr = PaddleOCR(text_detection_model_name="PP-OCRv5_mobile_det",
                                 text_recognition_model_name="PP-OCRv5_mobile_rec", **kwargs)
            self.models = "PP-OCRv5_mobile_det + PP-OCRv5_mobile_rec"
        except TypeError:
            self.ocr = PaddleOCR(lang=lang, enable_mkldnn=False, use_doc_orientation_classify=False,
                                 use_doc_unwarping=False, use_textline_orientation=False)
            self.models = "paddleocr default"
        self.lang = lang

    def detect(self, image_path: Path) -> list[dict[str, Any]]:
        out = []
        res = self.ocr.predict(str(image_path)) if hasattr(self.ocr, "predict") else self.ocr.ocr(str(image_path))
        for page in res:
            polys = page.get("dt_polys") if isinstance(page, dict) else None
            if polys is not None:
                texts, scores = page.get("rec_texts", []), page.get("rec_scores", [])
                for poly, text, score in zip(polys, texts, scores):
                    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
                    out.append({"text": text, "conf": float(score), "box": [min(xs), min(ys), max(xs), max(ys)]})
            else:  # legacy list format
                for item in page or []:
                    poly, (text, score) = item[0], item[1]
                    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
                    out.append({"text": text, "conf": float(score), "box": [min(xs), min(ys), max(xs), max(ys)]})
        return out


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
        # group words by line (block, par, line) into text lines
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


def load_backend() -> tuple[Any | None, str | None]:
    try:
        return _Paddle(), None
    except Exception as exc:  # noqa: BLE001
        first_line = (str(exc).strip().splitlines() or [""])[0][:240]
        paddle_err = f"paddleocr unavailable: {type(exc).__name__}: {first_line}".rstrip(": ")
    try:
        return _Tesseract(), None
    except Exception:  # noqa: BLE001
        return None, paddle_err + "; tesseract not found"


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


def extract_frames(src: Path, frame_ids: list[int], out_dir: Path, long_side: int, display_w: int, display_h: int) -> tuple[dict[int, Path], str | None]:
    """Write exactly these presented frames as JPEG, long side = `long_side`. Returns (files, error)."""
    from PIL import Image

    from . import decode

    if not frame_ids:
        return {}, None
    if display_h >= display_w:
        h = long_side - (long_side % 2); w = int(round(display_w * h / display_h)); w -= w % 2
    else:
        w = long_side - (long_side % 2); h = int(round(display_h * w / display_w)); h -= h % 2
    try:
        arrays, err = decode.pick_frames(src, frame_ids, max(2, w), max(2, h))
    except decode.DecodeError as exc:
        return {}, f"decode failed: {exc}"
    files: dict[int, Path] = {}
    for fid, rgb in arrays.items():
        f = out_dir / f"f_{fid:06d}.jpg"
        Image.fromarray(rgb).save(f, quality=92)
        files[fid] = f
    return files, err


# ----------------------------------------------------------------------------------------------- tracks
def _iou(a: list[float], b: list[float]) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def build_tracks(detections: dict[int, list[dict[str, Any]]], img_w: int, img_h: int, step: int, n_frames: int) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    open_tracks: list[dict[str, Any]] = []
    for fid in sorted(detections):
        dets = detections[fid]
        matched: set[int] = set()
        still_open = []
        for tr in open_tracks:
            best, best_i = None, -1
            for i, d in enumerate(dets):
                if i in matched:
                    continue
                nb = [d["box"][0] / img_w, d["box"][1] / img_h, d["box"][2] / img_w, d["box"][3] / img_h]
                sim = difflib.SequenceMatcher(None, tr["text"].lower(), d["text"].lower()).ratio()
                if _iou(tr["box"], nb) >= 0.4 and sim >= 0.6:
                    score = _iou(tr["box"], nb) + sim
                    if best is None or score > best:
                        best, best_i = score, i
            if best_i >= 0 and fid - tr["last_sampled_frame"] <= step * 2:
                d = dets[best_i]
                matched.add(best_i)
                tr["last_sampled_frame"] = fid
                tr["samples"].append(fid)
                if d["conf"] > tr["conf"]:
                    tr["text"], tr["conf"] = d["text"], d["conf"]
                still_open.append(tr)
            else:
                tracks.append(tr)
        open_tracks = still_open
        for i, d in enumerate(dets):
            if i in matched:
                continue
            nb = [d["box"][0] / img_w, d["box"][1] / img_h, d["box"][2] / img_w, d["box"][3] / img_h]
            open_tracks.append({"text": d["text"], "conf": d["conf"], "box": nb, "first_sampled_frame": fid,
                                "last_sampled_frame": fid, "samples": [fid]})
    tracks.extend(open_tracks)
    out = []
    for k, tr in enumerate(tracks):
        cy = (tr["box"][1] + tr["box"][3]) / 2
        zone = "upper_third" if cy < 1 / 3 else ("middle_band" if cy < 2 / 3 else "lower_third")
        rel_h = tr["box"][3] - tr["box"][1]
        width = tr["box"][2] - tr["box"][0]
        klass = "subtitle_candidate" if (zone != "upper_third" and width > 0.25 and rel_h < 0.12) else "text"
        out.append({
            "track_id": f"t{k:04d}", "text": tr["text"], "conf": round(tr["conf"], 3),
            "box_norm": [round(v, 4) for v in tr["box"]], "zone": zone, "rel_height": round(rel_h, 4),
            "frame_first_seen": tr["first_sampled_frame"], "frame_last_seen": tr["last_sampled_frame"],
            # candidate span: the text may have appeared up to (step-1) frames before the first sample
            "frame_first_candidate": max(0, tr["first_sampled_frame"] - (step - 1)),
            "frame_last_candidate": min(n_frames - 1, tr["last_sampled_frame"] + (step - 1)),
            "samples": len(tr["samples"]), "class": klass,
            "one_frame_candidate": len(tr["samples"]) == 1,
        })
    return out


def run(src: Path, ref_dir: Path, shots: list[dict[str, Any]], n_frames: int, display_w: int, display_h: int,
        index_frames: list[dict[str, Any]], mode: str = "economy") -> dict[str, Any]:
    backend, err = load_backend()
    if backend is None:
        return {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "status": "skipped", "reason": err,
                "sampled_frames": 0, "tracks": []}
    step = 1 if mode == "strict" else ECONOMY_STEP
    ids = sample_frame_ids(n_frames, shots, mode)
    tmp = Path(tempfile.mkdtemp(prefix="iris-ocr-", dir=str(ref_dir)))
    detections: dict[int, list[dict[str, Any]]] = {}
    img_w = img_h = None
    timings: list[float] = []
    try:
        files, extract_err = extract_frames(src, ids, tmp, OCR_LONG_SIDE, display_w, display_h)
        if len(files) != len(ids):
            return {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "status": "failed",
                    "reason": f"frame extraction returned {len(files)} of {len(ids)} frames: {extract_err or 'unknown'}",
                    "backend": backend.name, "sampled_frames": len(ids), "frames_done": 0, "tracks": []}
        for n, (fid, f) in enumerate(sorted(files.items())):
            if img_w is None:
                from PIL import Image

                with Image.open(f) as im:
                    img_w, img_h = im.size
            t0 = time.time()
            dets = backend.detect(f)
            dt = time.time() - t0
            timings.append(dt)
            # a backend that is pathologically slow is a broken environment, not a result: stop early and say so
            budget = FIRST_FRAME_BUDGET_S if n == 0 else FRAME_BUDGET_S * 4
            if dt > budget:
                return {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "status": "failed",
                        "reason": f"{backend.name} too slow: frame {n} took {dt:.1f} s (budget {budget:.0f} s); "
                                  f"check oneDNN/thread settings or the doc-preprocessing flags",
                        "backend": backend.name, "sampled_frames": len(ids), "frames_done": n, "tracks": []}
            if dets:
                detections[fid] = dets
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tracks = build_tracks(detections, img_w or 1, img_h or 1, step, n_frames) if detections else []
    pts = {f["frame_id"]: f.get("pts_time") for f in index_frames}
    for tr in tracks:
        tr["t_first_seen"] = pts.get(tr["frame_first_seen"])
        tr["t_last_seen"] = pts.get(tr["frame_last_seen"])
    return {
        "schema_version": "1.0.0", "method_version": METHOD_VERSION, "status": "ok",
        "backend": backend.name, "models": getattr(backend, "models", None), "lang": getattr(backend, "lang", None),
        "mode": mode, "step": step,
        "seconds_per_frame": round(sum(timings) / len(timings), 3) if timings else None,
        "sampled_frames": len(ids), "frames_with_text": len(detections), "detections": sum(len(v) for v in detections.values()),
        "image_size": [img_w, img_h], "tracks": tracks,
        "cue_timing_uncertainty_frames": step - 1,
    }
