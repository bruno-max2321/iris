"""Stage E: apparent camera motion (layer 1) and a subject/parallax residual (layers 2-3 proxy) from
phase correlation in numpy. No OpenCV needed; when cv2 is available a Farneback adapter can replace
this estimator behind the same output contract.

Per adjacent pair: global translation (dx, dy in px at analysis width), block translations on a
grid, divergence (radial component: + means expansion = apparent push-in), curl, residual (how much
blocks disagree with the global move: subject motion or parallax), and a jitter estimate.
Classification is per shot and always `estimated`; apparent_* labels carry alternatives."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from . import decode

METHOD_VERSION = "motion_phasecorr@0.3.0"
ANALYSIS_WIDTH = 192
GRID = (4, 3)  # rows, cols
TRIM_SHARE = 0.1            # largest-magnitude pairs left out of a shot's averages (a stray glitch, not the move)
BLOCK_MAJORITY = 0.5        # share of grid blocks that must agree to overrule the full-frame shift
BLOCK_AGREE_PX = 1.0        # a block agrees when its shift is this close to the blocks' median


def _hann2d(h: int, w: int) -> np.ndarray:
    return np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)


def phase_shift(a: np.ndarray, b: np.ndarray, win: np.ndarray) -> tuple[float, float, float]:
    """Translation that maps a -> b (dx, dy) and the peak response (0..1-ish confidence)."""
    fa = np.fft.fft2(a * win)
    fb = np.fft.fft2(b * win)
    r = fa * np.conj(fb)
    r /= np.maximum(np.abs(r), 1e-9)
    corr = np.real(np.fft.ifft2(r))
    peak = np.unravel_index(int(np.argmax(corr)), corr.shape)
    h, w = corr.shape
    dy = peak[0] if peak[0] <= h // 2 else peak[0] - h
    dx = peak[1] if peak[1] <= w // 2 else peak[1] - w
    conf = float(corr.max() / max(1e-9, np.abs(corr).sum() / corr.size) / corr.size * 100.0)
    # phase correlation returns the shift of b relative to a with opposite sign convention; normalise:
    return float(-dx), float(-dy), conf


def pair_metrics(prev: np.ndarray, cur: np.ndarray, cache: dict[str, Any]) -> dict[str, float]:
    h, w = cur.shape
    if "win_full" not in cache:
        cache["win_full"] = _hann2d(h, w)
        rows, cols = GRID
        bh, bw = h // rows, w // cols
        cache["blocks"] = [(r * bh, c * bw, bh, bw) for r in range(rows) for c in range(cols)]
        cache["win_block"] = _hann2d(bh, bw)
        cache["centers"] = np.array([[c * bw + bw / 2 - w / 2, r * bh + bh / 2 - h / 2] for r in range(rows) for c in range(cols)], dtype=np.float32)
    gdx, gdy, gconf = phase_shift(prev, cur, cache["win_full"])
    vecs = []
    for (y, x, bh, bw) in cache["blocks"]:
        dx, dy, _ = phase_shift(prev[y:y + bh, x:x + bw], cur[y:y + bh, x:x + bw], cache["win_block"])
        vecs.append((dx, dy))
    v = np.array(vecs, dtype=np.float32)
    # a fixed overlay (caption label, logo) gives the full-frame correlation a strong zero-shift peak, so a
    # pan under a caption reads as static; when most blocks agree on one shift, that is the camera's move
    med = np.median(v, axis=0)
    agree = np.linalg.norm(v - med, axis=1) <= BLOCK_AGREE_PX
    if agree.mean() >= BLOCK_MAJORITY and np.hypot(med[0] - gdx, med[1] - gdy) > BLOCK_AGREE_PX:
        gdx, gdy = float(med[0]), float(med[1])
    centers = cache["centers"]
    radial = centers / np.maximum(np.linalg.norm(centers, axis=1, keepdims=True), 1e-6)
    tangential = np.stack([-radial[:, 1], radial[:, 0]], axis=1)
    rel = v - np.array([gdx, gdy], dtype=np.float32)
    divergence = float(np.mean(np.sum(rel * radial, axis=1)))        # px/frame, + = expanding
    curl = float(np.mean(np.sum(rel * tangential, axis=1)))          # px/frame, rotation about centre
    residual = float(np.mean(np.linalg.norm(rel, axis=1)))           # disagreement with global move
    return {"dx": gdx, "dy": gdy, "conf": gconf, "div": divergence, "curl": curl, "resid": residual,
            "mag": float(np.hypot(gdx, gdy))}


def event_pairs(events: list[dict[str, Any]] | None) -> set[int]:
    """Pair indices touching a flash or short insert: their motion is the event, not the camera. A freeze
    is kept: a held picture is a static camera."""
    out: set[int] = set()
    for e in events or []:
        if e.get("type") not in ("flash", "short_insert"):
            continue
        f0, n = int(e["frame_first"]), max(1, int(e.get("length_frames") or 1))
        out.update(range(f0, f0 + n + 1))  # pair i is (i-1, i): pairs entering, inside and leaving the event
    return out


def classify(seg: list[dict[str, float]], sharp: np.ndarray, w: int, fps: float) -> dict[str, Any]:
    """Class of one shot from its pair metrics.

    Speed, direction and divergence are trimmed means: the TRIM_SHARE largest pairs are left out, so a
    stray glitch does not become a phantom pan. A median would be wrong here: animation drawn on twos or
    threes (common in motion graphics and archival photo moves) holds every other frame still, so most
    pairs are zero and the median of a steady pan is zero; the mean over all pairs is its real speed."""
    mag_all = np.array([p["mag"] for p in seg])
    keep = np.argsort(mag_all, kind="stable")[: len(seg) - int(len(seg) * TRIM_SHARE)] if len(seg) >= 5 else np.arange(len(seg))
    kept = [seg[i] for i in sorted(keep)]
    dx = np.array([p["dx"] for p in kept]); dy = np.array([p["dy"] for p in kept])
    div = np.array([p["div"] for p in kept])
    mean_dx, mean_dy = float(dx.mean()), float(dy.mean())
    pct_per_s = float(np.hypot(mean_dx, mean_dy) / w * 100.0 * fps)       # % of frame width per second, net
    div_pct_per_s = float(div.mean() / w * 100.0 * fps)
    # jitter: high-frequency part of the global translation (deviation from a 5-frame moving mean) over the
    # kept pairs; a held frame of on-twos animation also deviates, which is why sustained motion is
    # classified first
    k = min(5, len(dx))
    if k >= 3:
        kern = np.ones(k) / k
        jit = float(np.mean(np.hypot(dx - np.convolve(dx, kern, mode="same"), dy - np.convolve(dy, kern, mode="same"))))
    else:
        jit = 0.0
    med_sharp = float(np.median(sharp)) if len(sharp) > 1 else 0.0
    sharp_drop = float(1.0 - sharp.min() / med_sharp) if med_sharp > 1.0 else 0.0
    peak_pct_per_s = float(np.median(mag_all) / w * 100.0 * fps)

    # thresholds are starting values to calibrate in the pilot (percent of frame width per second)
    label, alts = "static", []
    if max(pct_per_s, peak_pct_per_s) > 150 and sharp_drop > 0.5:
        label, alts = "whip_pan", ["pan_left", "pan_right"]
    elif abs(div_pct_per_s) > 1.2 and abs(div_pct_per_s) * 2 > pct_per_s:
        label = "apparent_push_in" if div_pct_per_s > 0 else "apparent_pull_out"
        alts = ["dolly_in", "zoom_in", "digital_zoom"] if div_pct_per_s > 0 else ["dolly_out", "zoom_out", "digital_zoom"]
    elif pct_per_s > 3.0:
        if abs(mean_dx) >= abs(mean_dy):
            # content moving left on screen (dx < 0) means the camera pans right
            label, alts = ("pan_right" if mean_dx < 0 else "pan_left"), ["dolly_right" if mean_dx < 0 else "dolly_left", "apparent_lateral_travel"]
        else:
            label, alts = ("tilt_up" if mean_dy > 0 else "tilt_down"), ["crane_up" if mean_dy > 0 else "crane_down", "apparent_vertical_travel"]
    elif jit / w * 100.0 * fps > 2.5:
        label, alts = "handheld", ["static"]
    return {"class": label, "alternatives": alts, "pct_per_s": pct_per_s, "div_pct_per_s": div_pct_per_s, "dx": mean_dx, "dy": mean_dy,
            "jit": jit, "sharp_drop": sharp_drop, "pairs_trimmed": len(seg) - len(kept)}


def run(src: Path, display_w: int, display_h: int, shots: list[dict[str, Any]], frames: list[dict[str, Any]],
        fps: float, events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    w, h = decode.analysis_size(display_w, display_h, ANALYSIS_WIDTH)
    cache: dict[str, Any] = {}
    prev: np.ndarray | None = None
    pairs: list[dict[str, float]] = []
    for rgb in decode.iter_frames(src, w, h):
        g = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]).astype(np.float32)
        if prev is not None:
            pairs.append(pair_metrics(prev, g, cache))
        prev = g
    n_pairs = len(pairs)
    sharp = np.array([f.get("sharpness") or 0.0 for f in frames], dtype=float)

    per_shot: list[dict[str, Any]] = []
    skip = event_pairs(events)
    for s in shots:
        a, b = s["frame_first"], s["frame_last_inclusive"]
        seg = [p for i, p in enumerate(pairs, start=1) if a < i <= b and i not in skip]   # pair i is (i-1, i)
        if not seg:
            per_shot.append({"shot_id": s["shot_id"], "status": "too_short", "class": "unclear"})
            continue
        c = classify(seg, sharp[a:b + 1], w, fps)
        label, alts = c["class"], c["alternatives"]
        pct_per_s, div_pct_per_s, mean_dx, mean_dy = c["pct_per_s"], c["div_pct_per_s"], c["dx"], c["dy"]
        jit, sharp_drop = c["jit"], c["sharp_drop"]
        curl = np.array([p["curl"] for p in seg]); resid = np.array([p["resid"] for p in seg]); conf = np.array([p["conf"] for p in seg])
        per_shot.append({
            "shot_id": s["shot_id"], "status": "ok",
            "class": label, "alternatives": alts, "claim_kind": "estimated",
            "flow_magnitude_pct_w_per_s": round(pct_per_s, 3),
            "flow_direction_deg": round(float(np.degrees(np.arctan2(-mean_dy, mean_dx))), 1),
            "flow_divergence_pct_w_per_s": round(div_pct_per_s, 3),
            "flow_curl_px_per_frame": round(float(curl.mean()), 4),
            "flow_jitter_pct_w_per_s": round(float(jit / w * 100.0 * fps), 3),
            "subject_vs_background_residual_px": round(float(resid.mean()), 3),
            "parallax_ratio": None,
            "phase_confidence_mean": round(float(conf.mean()), 4),
            "sharpness_drop": round(sharp_drop, 3),
            "pairs": len(seg),
        })
    return {
        "schema_version": "1.0.0", "method_version": METHOD_VERSION,
        "analysis_width": w, "analysis_height": h, "grid": list(GRID), "pairs": n_pairs,
        "per_pair": [[round(p["dx"], 3), round(p["dy"], 3), round(p["div"], 4), round(p["curl"], 4), round(p["resid"], 3), round(p["conf"], 4)] for p in pairs],
        "per_pair_columns": ["dx_px", "dy_px", "div_px", "curl_px", "resid_px", "conf"],
        "shots": per_shot,
        "notes": ["dx>0 means content moves right on screen; pan_right is assigned when content moves left",
                  "divergence>0 means expansion (apparent push-in); mechanism is not resolved without parallax evidence",
                  "parallax_ratio is null in the phase-correlation estimator; a Farneback/feature adapter fills it"],
    }
