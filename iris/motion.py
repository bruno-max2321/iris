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

METHOD_VERSION = "motion_phasecorr@0.1.1"
ANALYSIS_WIDTH = 192
GRID = (4, 3)  # rows, cols


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
    centers = cache["centers"]
    radial = centers / np.maximum(np.linalg.norm(centers, axis=1, keepdims=True), 1e-6)
    tangential = np.stack([-radial[:, 1], radial[:, 0]], axis=1)
    rel = v - np.array([gdx, gdy], dtype=np.float32)
    divergence = float(np.mean(np.sum(rel * radial, axis=1)))        # px/frame, + = expanding
    curl = float(np.mean(np.sum(rel * tangential, axis=1)))          # px/frame, rotation about centre
    residual = float(np.mean(np.linalg.norm(rel, axis=1)))           # disagreement with global move
    return {"dx": gdx, "dy": gdy, "conf": gconf, "div": divergence, "curl": curl, "resid": residual,
            "mag": float(np.hypot(gdx, gdy))}


def run(src: Path, display_w: int, display_h: int, shots: list[dict[str, Any]], frames: list[dict[str, Any]],
        fps: float) -> dict[str, Any]:
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
    for s in shots:
        a, b = s["frame_first"], s["frame_last_inclusive"]
        seg = [p for i, p in enumerate(pairs, start=1) if a < i <= b]   # pair i is (i-1, i)
        if not seg:
            per_shot.append({"shot_id": s["shot_id"], "status": "too_short", "class": "unclear"})
            continue
        dx = np.array([p["dx"] for p in seg]); dy = np.array([p["dy"] for p in seg])
        mag = np.hypot(dx, dy)
        div = np.array([p["div"] for p in seg]); curl = np.array([p["curl"] for p in seg])
        resid = np.array([p["resid"] for p in seg]); conf = np.array([p["conf"] for p in seg])
        # jitter: high-frequency part of the global translation (deviation from a 5-frame moving mean)
        k = min(5, len(dx))
        if k >= 3:
            kern = np.ones(k) / k
            jit = float(np.mean(np.hypot(dx - np.convolve(dx, kern, mode="same"), dy - np.convolve(dy, kern, mode="same"))))
        else:
            jit = 0.0
        # medians: a one-frame insert or flash inside the shot produces one or two wild pairs that a mean
        # would turn into a phantom pan; the median keeps the sustained motion
        pct_per_s = float(np.median(mag) / w * 100.0 * fps)       # % of frame width per second
        div_pct_per_s = float(np.median(div) / w * 100.0 * fps)
        mean_dx, mean_dy = float(np.median(dx)), float(np.median(dy))
        med_sharp = float(np.median(sharp[a:b + 1])) if b > a else 0.0
        sharp_drop = float(1.0 - sharp[a:b + 1].min() / med_sharp) if med_sharp > 1.0 else 0.0

        # thresholds are starting values to calibrate in the pilot (percent of frame width per second)
        label, alts = "static", []
        if pct_per_s > 150 and sharp_drop > 0.5:
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
