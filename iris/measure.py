"""Stage C: per-frame measurements in numpy. Every value is computed on the analysis-size frame and
the resolution and transform are recorded alongside. Column names match the measurement keys used by
the vocabulary (frames.*)."""

from __future__ import annotations

from typing import Any

import numpy as np

METHOD_VERSION = "measure@0.1.0"
COLUMNS = [
    "frame_id", "L_mean", "L_std", "L_p5", "L_p95", "L_hist16", "a_mean", "b_mean",
    "sat_mean", "sat_p90", "colorfulness", "contrast_rms", "clip_highlights", "clip_shadows",
    "sharpness", "edge_density", "diff_prev", "hist_diff_prev", "phash", "band_top_L", "band_safe_L",
]

# sRGB -> XYZ (D65) matrix
_M = np.array([[0.4124564, 0.3575761, 0.1804375],
               [0.2126729, 0.7151522, 0.0721750],
               [0.0193339, 0.1191920, 0.9503041]], dtype=np.float32)
_WHITE = np.array([0.95047, 1.0, 1.08883], dtype=np.float32)


def srgb_to_lab(rgb_u8: np.ndarray) -> np.ndarray:
    rgb = rgb_u8.astype(np.float32) / 255.0
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = lin @ _M.T / _WHITE
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16.0 / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def hsv_saturation(rgb_u8: np.ndarray) -> np.ndarray:
    rgb = rgb_u8.astype(np.float32)
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)


def colorfulness(rgb_u8: np.ndarray) -> float:
    """Hasler & Süsstrunk (2003)."""
    r, g, b = (rgb_u8[..., i].astype(np.float32) for i in range(3))
    rg = r - g
    yb = 0.5 * (r + g) - b
    return float(np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2))


def gray(rgb_u8: np.ndarray) -> np.ndarray:
    rgb = rgb_u8.astype(np.float32)
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def laplacian_var(g: np.ndarray) -> float:
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    return float(lap.var())


def edge_density(g: np.ndarray, thresh: float = 40.0) -> float:
    gx = g[1:-1, 2:] - g[1:-1, :-2]
    gy = g[2:, 1:-1] - g[:-2, 1:-1]
    mag = np.hypot(gx, gy)
    return float((mag > thresh).mean())


def phash(g: np.ndarray, hash_size: int = 8, highfreq: int = 4) -> str:
    """Perceptual hash: 32x32 area-resample, DCT, top-left 8x8 (minus DC) vs median."""
    n = hash_size * highfreq
    h, w = g.shape
    ys = (np.arange(n) * h / n).astype(int)
    xs = (np.arange(n) * w / n).astype(int)
    small = np.ascontiguousarray(g[np.ix_(ys, xs)], dtype=np.float64)
    k = np.arange(n, dtype=np.float64)
    c = np.ascontiguousarray(np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n)))
    # Accelerate BLAS on macOS emits spurious FP warnings on these matmuls; results are finite.
    with np.errstate(all="ignore"):
        dct = np.dot(np.dot(c, small), c.T)
    low = dct[:hash_size, :hash_size].flatten()[1:]
    if not np.all(np.isfinite(low)):
        low = np.nan_to_num(low)
    bits = low > np.median(low)
    val = 0
    for b in bits:
        val = (val << 1) | int(b)
    return f"{val:016x}"


def hist16(L: np.ndarray) -> np.ndarray:
    h, _ = np.histogram(L, bins=16, range=(0.0, 100.0))
    return h / max(1, L.size)


class FrameMeasurer:
    """Stateful over consecutive frames (needs the previous frame for differences)."""

    def __init__(self, width: int, height: int, frame_h_full: int, safe_top_px: int = 240, safe_bottom_px: int = 660,
                 top_band_frac: float = 0.125) -> None:
        self.width, self.height = width, height
        self.scale = height / max(1, frame_h_full)
        self.top_rows = max(1, int(height * top_band_frac))
        self.safe_y0 = int(round(safe_top_px * self.scale))
        self.safe_y1 = max(self.safe_y0 + 1, height - int(round(safe_bottom_px * self.scale)))
        self._prev_L: np.ndarray | None = None
        self._prev_hist: np.ndarray | None = None

    def measure(self, frame_id: int, rgb: np.ndarray) -> dict[str, Any]:
        lab = srgb_to_lab(rgb)
        L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
        g = gray(rgb)
        sat = hsv_saturation(rgb)
        hist = hist16(L)
        row: dict[str, Any] = {
            "frame_id": frame_id,
            "L_mean": float(L.mean()), "L_std": float(L.std()),
            "L_p5": float(np.percentile(L, 5)), "L_p95": float(np.percentile(L, 95)),
            "L_hist16": [round(float(x), 5) for x in hist],
            "a_mean": float(a.mean()), "b_mean": float(b.mean()),
            "sat_mean": float(sat.mean()), "sat_p90": float(np.percentile(sat, 90)),
            "colorfulness": colorfulness(rgb),
            "contrast_rms": float(L.std() / 100.0),
            "clip_highlights": float((rgb.max(axis=-1) >= 250).mean()),
            "clip_shadows": float((rgb.max(axis=-1) <= 5).mean()),
            "sharpness": laplacian_var(g),
            "edge_density": edge_density(g),
            "diff_prev": None if self._prev_L is None else float(np.abs(L - self._prev_L).mean() / 100.0),
            "hist_diff_prev": None if self._prev_hist is None else float(1.0 - np.minimum(hist, self._prev_hist).sum()),
            "phash": phash(g),
            "band_top_L": float(L[: self.top_rows].mean()),
            "band_safe_L": float(L[self.safe_y0:self.safe_y1].mean()),
        }
        self._prev_L, self._prev_hist = L, hist
        return row

    def transform(self) -> dict[str, Any]:
        return {"analysis_width": self.width, "analysis_height": self.height, "resample": "area",
                "color_space_assumed": "sRGB/BT.709 for Lab", "method_version": METHOD_VERSION,
                "safe_zone_rows": [self.safe_y0, self.safe_y1], "top_band_rows": self.top_rows}
