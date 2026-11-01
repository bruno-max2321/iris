"""Stage G: coarse automatic regions, per-region colour, light attributes and ΔE2000 continuity.

Regions are `estimated` and carry their frame coverage. Without MediaPipe, skin comes from a YCbCr
colour model, the subject from a centre-weighted saliency proxy (edge density × saturation), graphics
from OCR tracks, and background is the remainder. A MediaPipe adapter can replace the skin/subject
estimators behind the same output contract."""

from __future__ import annotations

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from . import measure

METHOD_VERSION = "regions@0.1.0"
KEYFRAME_WIDTH = 320


def extract_keyframes(src: Path, frame_ids: list[int], out_dir: Path, width: int, display_w: int, display_h: int) -> dict[int, np.ndarray]:
    from PIL import Image

    if not frame_ids:
        return {}
    h = int(round(display_h * width / display_w)); h -= h % 2
    expr = "+".join(f"eq(n\\,{i})" for i in frame_ids)
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(src), "-fps_mode", "passthrough", "-an",
                    "-vf", f"select='{expr}',scale={width}:{h}:flags=area", str(out_dir / "k_%06d.png")],
                   check=False, capture_output=True, timeout=1800)
    files = sorted(out_dir.glob("k_*.png"))
    out = {}
    for fid, f in zip(frame_ids, files):
        with Image.open(f) as im:
            out[fid] = np.asarray(im.convert("RGB"))
    return out


def skin_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return (cb >= 77) & (cb <= 127) & (cr >= 133) & (cr <= 173) & (y > 40)


def subject_box(rgb: np.ndarray) -> tuple[int, int, int, int] | None:
    """Centre-weighted saliency on a 6x6 grid: edge density × (0.3 + saturation). Returns (x0,y0,x1,y1)."""
    g = measure.gray(rgb)
    sat = measure.hsv_saturation(rgb)
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    edges = (np.hypot(gx, gy) > 25).astype(np.float32)
    h, w = edges.shape
    rows, cols = 6, 6
    cell = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            ys, xs = slice(r * h // rows, (r + 1) * h // rows), slice(c * w // cols, (c + 1) * w // cols)
            weight = 1.0 - 0.5 * np.hypot((r + 0.5) / rows - 0.5, (c + 0.5) / cols - 0.5) * 2
            cell[r, c] = edges[ys, xs].mean() * (0.3 + sat[ys, xs].mean()) * weight
    if cell.max() <= 1e-4:
        return None
    thr = cell.max() * 0.55
    rs, cs = np.where(cell >= thr)
    y0, y1 = rs.min() * h // rows, (rs.max() + 1) * h // rows
    x0, x1 = cs.min() * w // cols, (cs.max() + 1) * w // cols
    return int(x0), int(y0), int(x1), int(y1)


def kmeans_palette(pixels: np.ndarray, k: int = 4, iters: int = 12, seed: int = 0) -> list[dict[str, Any]]:
    if len(pixels) == 0:
        return []
    rng = np.random.RandomState(seed)
    px = pixels.astype(np.float32)
    if len(px) > 4000:
        px = px[rng.choice(len(px), 4000, replace=False)]
    k = min(k, len(px))
    centers = px[rng.choice(len(px), k, replace=False)]
    for _ in range(iters):
        d = ((px[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                centers[j] = px[m].mean(0)
    d = ((px[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1)
    out = []
    for j in np.argsort(-np.bincount(lab, minlength=k)):
        share = float((lab == j).mean())
        c = np.clip(centers[j], 0, 255).astype(int)
        out.append({"hex": "#%02X%02X%02X" % tuple(int(x) for x in c), "share": round(share, 3)})
    return out


def region_stats(rgb: np.ndarray, mask: np.ndarray) -> dict[str, Any] | None:
    if mask.sum() < 50:
        return None
    px = rgb[mask]
    lab = measure.srgb_to_lab(px)
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    sat = measure.hsv_saturation(px)
    return {
        "coverage": round(float(mask.mean()), 4),
        "L": {"p5": round(float(np.percentile(L, 5)), 2), "p50": round(float(np.percentile(L, 50)), 2), "p95": round(float(np.percentile(L, 95)), 2), "mean": round(float(L.mean()), 2)},
        "a_mean": round(float(a.mean()), 2), "b_mean": round(float(b.mean()), 2),
        "sat_mean": round(float(sat.mean()), 4),
        "palette": kmeans_palette(px),
        "lab_mean": [round(float(L.mean()), 3), round(float(a.mean()), 3), round(float(b.mean()), 3)],
    }


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
    L1, a1, b1 = lab1; L2, a2, b2 = lab2
    C1 = np.hypot(a1, b1); C2 = np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360; h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1; dCp = C2p - C1p
    dhp = h2p - h1p
    if C1p * C2p == 0:
        dhp = 0
    elif dhp > 180:
        dhp -= 360
    elif dhp < -180:
        dhp += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2))
    Lpm = (L1 + L2) / 2; Cpm = (C1p + C2p) / 2
    hsum = h1p + h2p
    if C1p * C2p == 0:
        hpm = hsum
    elif abs(h1p - h2p) <= 180:
        hpm = hsum / 2
    else:
        hpm = (hsum + 360) / 2 if hsum < 360 else (hsum - 360) / 2
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) - 0.20 * np.cos(np.radians(4 * hpm - 63))
    dtheta = 30 * np.exp(-((hpm - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    Sc = 1 + 0.045 * Cpm; Sh = 1 + 0.015 * Cpm * T
    Rt = -np.sin(np.radians(2 * dtheta)) * Rc
    return float(np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh)))


def light_attributes(rgb: np.ndarray, box: tuple[int, int, int, int] | None) -> dict[str, Any]:
    lab = measure.srgb_to_lab(rgb)
    L = lab[..., 0]
    if box is None:
        sub = L
    else:
        x0, y0, x1, y1 = box
        sub = L[y0:y1, x0:x1]
    med = float(np.median(sub))
    key = "high_key" if med >= 65 else ("low_key" if med < 35 else "mid_key")
    w = sub.shape[1]
    left, right = float(sub[:, : w // 2].mean()), float(sub[:, w // 2:].mean())
    asym = (left - right) / max(1e-6, (left + right) / 2)
    if abs(asym) <= 0.08:
        side = "key_centred"
    else:
        side = "key_screen_left" if asym > 0 else "key_screen_right"
    p5, p95 = float(np.percentile(sub, 5)), float(np.percentile(sub, 95))
    contrast_ratio = p95 / max(1.0, p5)
    g = sub
    gx = np.abs(np.diff(g, axis=1)); gy = np.abs(np.diff(g, axis=0))
    grad = np.concatenate([gx.ravel(), gy.ravel()])
    strong = grad[grad > np.percentile(grad, 90)] if grad.size else grad
    edge_softness = float(np.median(strong)) if strong.size else 0.0   # higher = harder transitions
    edge = "hard_light" if edge_softness > 12 else "soft_light"
    return {"key": key, "L_median": round(med, 2), "side": side, "luma_asymmetry": round(float(asym), 4),
            "contrast_ratio_p95_p5": round(contrast_ratio, 3), "edge_gradient_p90_median": round(edge_softness, 3),
            "edge": edge, "claim_kind": "estimated"}


def run(src: Path, ref_dir: Path, shots: list[dict[str, Any]], display_w: int, display_h: int,
        text_tracks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    mids = [s["keyframes"]["mid"] for s in shots]
    tmp = Path(tempfile.mkdtemp(prefix="iris-regions-", dir=str(ref_dir)))
    try:
        frames = extract_keyframes(src, mids, tmp, KEYFRAME_WIDTH, display_w, display_h)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    per_shot = []
    for s in shots:
        rgb = frames.get(s["keyframes"]["mid"])
        if rgb is None:
            per_shot.append({"shot_id": s["shot_id"], "status": "keyframe_missing"})
            continue
        h, w, _ = rgb.shape
        skin = skin_mask(rgb)
        box = subject_box(rgb)
        subj = np.zeros((h, w), dtype=bool)
        if box:
            subj[box[1]:box[3], box[0]:box[2]] = True
        graphics = np.zeros((h, w), dtype=bool)
        for tr in text_tracks or []:
            if tr["frame_first_candidate"] <= s["keyframes"]["mid"] <= tr["frame_last_candidate"]:
                x0, y0, x1, y1 = tr["box_norm"]
                graphics[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = True
        subj &= ~skin & ~graphics
        background = ~(skin | subj | graphics)
        regions = {
            "skin": region_stats(rgb, skin), "subject": region_stats(rgb, subj),
            "graphics": region_stats(rgb, graphics), "background": region_stats(rgb, background),
            "whole_frame": region_stats(rgb, np.ones((h, w), dtype=bool)),
        }
        per_shot.append({"shot_id": s["shot_id"], "status": "ok", "keyframe": s["keyframes"]["mid"],
                         "subject_box_norm": None if box is None else [round(box[0] / w, 3), round(box[1] / h, 3), round(box[2] / w, 3), round(box[3] / h, 3)],
                         "regions": regions, "light": light_attributes(rgb, box)})
    # masters: median Lab per region across shots; ΔE per shot vs master and vs previous shot
    for region in ("background", "subject", "skin", "graphics", "whole_frame"):
        labs = [np.array(ps["regions"][region]["lab_mean"]) for ps in per_shot if ps.get("status") == "ok" and ps["regions"].get(region)]
        if not labs:
            continue
        master = np.median(np.stack(labs), axis=0)
        prev = None
        for ps in per_shot:
            r = ps.get("regions", {}).get(region) if ps.get("status") == "ok" else None
            if not r:
                prev = None
                continue
            cur = np.array(r["lab_mean"])
            r["delta_e2000_vs_master"] = round(ciede2000(master, cur), 3)
            r["delta_e2000_vs_prev"] = None if prev is None else round(ciede2000(prev, cur), 3)
            prev = cur
    de = [ps["regions"]["background"]["delta_e2000_vs_master"] for ps in per_shot if ps.get("status") == "ok" and ps["regions"].get("background") and "delta_e2000_vs_master" in ps["regions"]["background"]]
    summary = {
        "background_delta_e_vs_master": None if not de else {"p50": round(float(np.percentile(de, 50)), 3), "p90": round(float(np.percentile(de, 90)), 3), "max": round(float(max(de)), 3)},
        "key_distribution": _dist([ps["light"]["key"] for ps in per_shot if ps.get("status") == "ok"]),
        "side_distribution": _dist([ps["light"]["side"] for ps in per_shot if ps.get("status") == "ok"]),
        "edge_distribution": _dist([ps["light"]["edge"] for ps in per_shot if ps.get("status") == "ok"]),
    }
    return {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "keyframe_width": KEYFRAME_WIDTH,
            "estimators": {"skin": "ycbcr_color_model", "subject": "edge_saturation_saliency_6x6", "graphics": "ocr_tracks", "background": "remainder"},
            "shots": per_shot, "summary": summary,
            "notes": ["all regions are estimated; coverage is the share of the keyframe each mask covers",
                      "light.side uses luma asymmetry of the subject box; without a face it is a weak proxy"]}


def _dist(labels: list[str]) -> dict[str, float]:
    if not labels:
        return {}
    out: dict[str, float] = {}
    for x in labels:
        out[x] = out.get(x, 0) + 1
    return {k: round(v / len(labels), 3) for k, v in sorted(out.items(), key=lambda kv: -kv[1])}
