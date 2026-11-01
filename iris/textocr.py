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
from pathlib import Path
from typing import Any

METHOD_VERSION = "textocr@0.1.0"
OCR_LONG_SIDE = 960
ECONOMY_STEP = 6


# ----------------------------------------------------------------------------------------------- backends
class _Paddle:
    name = "paddleocr-mobile"

    def __init__(self) -> None:
        from paddleocr import PaddleOCR  # type: ignore

        lang = os.environ.get("IRIS_OCR_LANG", "en")
        kwargs = dict(lang=lang, enable_mkldnn=False, text_det_limit_side_len=OCR_LONG_SIDE, use_textline_orientation=False)
        try:
            self.ocr = PaddleOCR(ocr_version="PP-OCRv5", text_detection_model_name="PP-OCRv5_mobile_det",
                                 text_recognition_model_name="PP-OCRv5_mobile_rec", **kwargs)
        except TypeError:
            self.ocr = PaddleOCR(lang=lang, enable_mkldnn=False)
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
        paddle_err = f"paddleocr unavailable: {type(exc).__name__}"
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


def extract_frames(src: Path, frame_ids: list[int], out_dir: Path, long_side: int, display_w: int, display_h: int) -> dict[int, Path]:
    """Extract exactly these presented frames as JPEG, scaled so the long side is `long_side`."""
    if not frame_ids:
        return {}
    if display_h >= display_w:
        scale = f"scale=-2:{long_side}"
    else:
        scale = f"scale={long_side}:-2"
    expr = "+".join(f"eq(n\\,{i})" for i in frame_ids)
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(src), "-fps_mode", "passthrough", "-an",
           "-vf", f"select='{expr}',{scale}", "-q:v", "3", str(out_dir / "f_%06d.jpg")]
    subprocess.run(cmd, check=False, capture_output=True, timeout=1800)
    files = sorted(out_dir.glob("f_*.jpg"))
    return {fid: f for fid, f in zip(frame_ids, files)}


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
    try:
        files = extract_frames(src, ids, tmp, OCR_LONG_SIDE, display_w, display_h)
        for fid, f in files.items():
            if img_w is None:
                from PIL import Image

                with Image.open(f) as im:
                    img_w, img_h = im.size
            dets = backend.detect(f)
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
        "backend": backend.name, "lang": getattr(backend, "lang", None), "mode": mode, "step": step,
        "sampled_frames": len(ids), "frames_with_text": len(detections), "detections": sum(len(v) for v in detections.values()),
        "image_size": [img_w, img_h], "tracks": tracks,
        "cue_timing_uncertainty_frames": step - 1,
    }
