"""Stage I: contact sheets and plots. ffmpeg `tile` for sheets (drawtext timecode when the build has
libfreetype, fixed time-per-sheet otherwise), PIL for the palette strip and the measurement plots."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def _has_drawtext() -> bool:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return " drawtext " in (p.stdout or "")


def timeline_sheets(src: Path, out_dir: Path, fps_sample: float = 2.0, cols: int = 6, rows: int = 10, thumb_w: int = 180) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    draw = _has_drawtext()
    vf = f"fps={fps_sample},scale={thumb_w}:-2"
    if draw:
        vf += ",drawtext=text='%{pts\\:hms}  n=%{n}':x=4:y=4:fontsize=12:fontcolor=white:box=1:boxcolor=black@0.6"
    vf += f",tile={cols}x{rows}"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-vf", vf, str(out_dir / "timeline_%02d.png")],
                   check=False, capture_output=True, timeout=1800)
    pages = sorted(out_dir.glob("timeline_*.png"))
    return {"pages": [p.name for p in pages], "fps_sample": fps_sample, "grid": [cols, rows],
            "seconds_per_page": cols * rows / fps_sample, "timecode_burned": draw,
            "note": None if draw else "no drawtext in this ffmpeg: each page covers a fixed span; frame k of page p is at t = (p*cols*rows + k) / fps_sample"}


def shot_sheet(src: Path, out_dir: Path, shots: list[dict[str, Any]], thumb_w: int = 240, per_page: int = 12) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ids: list[int] = []
    for s in shots:
        ids += [s["keyframes"]["first"], s["keyframes"]["mid"], s["keyframes"]["last"]]
    pages = []
    for p in range(0, len(shots), per_page):
        chunk = ids[p * 3:(p + per_page) * 3]
        if not chunk:
            break
        expr = "+".join(f"eq(n\\,{i})" for i in sorted(set(chunk)))
        rows = max(1, len(chunk) // 3)
        out = out_dir / f"shots_{p // per_page:02d}.png"
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-fps_mode", "passthrough", "-an",
                        "-vf", f"select='{expr}',scale={thumb_w}:-2,tile=3x{rows}", "-frames:v", "1", str(out)],
                       check=False, capture_output=True, timeout=1800)
        if out.exists():
            pages.append(out.name)
    return {"pages": pages, "layout": "3 columns per shot: first, mid, last", "shots_per_page": per_page}


def palette_strip(out_path: Path, shots: list[dict[str, Any]], regions_doc: dict[str, Any], width: int = 1080, height: int = 160) -> bool:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    total = sum(max(0.001, s["duration_s"]) for s in shots) or 1.0
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    by_id = {ps["shot_id"]: ps for ps in regions_doc.get("shots", [])}
    x = 0.0
    for s in shots:
        w = width * max(0.001, s["duration_s"]) / total
        ps = by_id.get(s["shot_id"])
        bands = []
        if ps and ps.get("status") == "ok":
            for region in ("background", "subject", "skin"):
                r = ps["regions"].get(region)
                if r and r.get("palette"):
                    bands.append(r["palette"][0]["hex"])
        if not bands:
            v = int(255 * s["L_mean"] / 100)
            bands = ["#%02X%02X%02X" % (v, v, v)]
        bh = height / len(bands)
        for i, hx in enumerate(bands):
            d.rectangle((x, i * bh, x + w, (i + 1) * bh), fill=hx)
        x += w
    img.save(out_path)
    return True


def plots(out_path: Path, frames: list[dict[str, Any]], shots: list[dict[str, Any]], width: int = 1200, height: int = 360) -> bool:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False
    n = max(1, len(frames))
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    series = [("L_mean", (43, 43, 43), 100.0), ("sat_mean", (158, 120, 82), 1.0), ("hist_diff_prev", (200, 60, 60), 1.0)]
    for key, color, scale in series:
        pts = []
        for f in frames:
            v = f.get(key)
            if v is None:
                continue
            pts.append((f["frame_id"] / n * width, height - 10 - min(1.0, float(v) / scale) * (height - 20)))
        if len(pts) > 1:
            d.line(pts, fill=color, width=1)
    for s in shots[1:]:
        xx = s["frame_first"] / n * width
        d.line([(xx, 0), (xx, height)], fill=(180, 180, 180), width=1)
    img.save(out_path)
    return True


def run(src: Path, ref_dir: Path, shots: list[dict[str, Any]], frames: list[dict[str, Any]], regions_doc: dict[str, Any] | None) -> dict[str, Any]:
    out_dir = ref_dir / "sheets"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    tl = timeline_sheets(src, out_dir)
    ss = shot_sheet(src, out_dir, shots)
    strip = palette_strip(out_dir / "palette_strip.png", shots, regions_doc or {})
    pl = plots(out_dir / "curves.png", frames, shots)
    return {"schema_version": "1.0.0", "timeline": tl, "shots": ss,
            "palette_strip": "palette_strip.png" if strip else None, "curves": "curves.png" if pl else None}
