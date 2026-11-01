"""ffprobe wrappers. Everything about a file that can be known without decoding pixels.

The frame index comes from `ffprobe -show_frames` so every presented frame has a PTS in stream time
base. Time is never derived as frame_id / fps."""

from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any


class ProbeError(RuntimeError):
    """The container or stream could not be read."""


def _ffprobe(args: list[str], timeout: int = 300) -> dict[str, Any]:
    exe = shutil.which("ffprobe")
    if not exe:
        raise ProbeError("ffprobe not found on PATH")
    p = subprocess.run([exe, "-v", "error", "-of", "json", *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise ProbeError((p.stderr or "ffprobe failed").strip()[-400:])
    try:
        return json.loads(p.stdout or "{}")
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise ProbeError(f"ffprobe returned invalid JSON: {exc}") from exc


def probe_container(path: Path) -> dict[str, Any]:
    """Format and stream metadata. Raises ProbeError when the container is unreadable."""
    data = _ffprobe(["-show_format", "-show_streams", str(path)])
    if not data.get("streams"):
        raise ProbeError("no streams found")
    return data


def _fraction(text: str | None) -> float | None:
    if not text or text in ("0/0", "N/A"):
        return None
    try:
        return float(Fraction(text))
    except (ValueError, ZeroDivisionError):
        return None


def rotation_degrees(stream: dict[str, Any]) -> int:
    """Rotation from display-matrix side data or legacy `rotate` tag. 0 when absent."""
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            try:
                return int(round(float(sd["rotation"]))) % 360
            except (TypeError, ValueError):
                continue
    tag = (stream.get("tags") or {}).get("rotate")
    if tag is not None:
        try:
            return int(round(float(tag))) % 360
        except (TypeError, ValueError):
            return 0
    return 0


def summarize(container: dict[str, Any]) -> dict[str, Any]:
    """Compact, stable summary stored in manifest.json."""
    fmt = container.get("format", {})
    video = next((s for s in container["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in container["streams"] if s.get("codec_type") == "audio"), None)
    if video is None:
        raise ProbeError("no video stream")
    rot = rotation_degrees(video)
    coded_w, coded_h = int(video.get("width", 0)), int(video.get("height", 0))
    if rot in (90, 270):
        disp_w, disp_h = coded_h, coded_w
    else:
        disp_w, disp_h = coded_w, coded_h
    sar = _fraction(video.get("sample_aspect_ratio")) or 1.0
    return {
        "format_name": fmt.get("format_name"),
        "duration_s": float(fmt["duration"]) if fmt.get("duration") else None,
        "bit_rate": int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
        "video": {
            "index": video.get("index"),
            "codec": video.get("codec_name"),
            "profile": video.get("profile"),
            "pix_fmt": video.get("pix_fmt"),
            "coded_width": coded_w,
            "coded_height": coded_h,
            "display_width": disp_w,
            "display_height": disp_h,
            "rotation": rot,
            "sample_aspect_ratio": sar,
            "r_frame_rate": video.get("r_frame_rate"),
            "avg_frame_rate": video.get("avg_frame_rate"),
            "nominal_fps": _fraction(video.get("avg_frame_rate")) or _fraction(video.get("r_frame_rate")),
            "time_base": video.get("time_base"),
            "nb_frames_declared": int(video["nb_frames"]) if str(video.get("nb_frames", "")).isdigit() else None,
            "duration_s": float(video["duration"]) if video.get("duration") else None,
            "color_primaries": video.get("color_primaries"),
            "color_transfer": video.get("color_transfer"),
            "color_space": video.get("color_space"),
            "color_range": video.get("color_range"),
            "hdr": (video.get("color_transfer") or "").lower() in {"smpte2084", "arib-std-b67"},
        },
        "audio": None if audio is None else {
            "index": audio.get("index"),
            "codec": audio.get("codec_name"),
            "sample_rate": int(audio["sample_rate"]) if audio.get("sample_rate") else None,
            "channels": audio.get("channels"),
            "duration_s": float(audio["duration"]) if audio.get("duration") else None,
        },
    }


def frame_index(path: Path) -> list[dict[str, Any]]:
    """One record per presented video frame, in presentation order, with PTS in seconds."""
    data = _ffprobe([
        "-select_streams", "v:0",
        "-show_entries", "frame=pts,pts_time,duration,duration_time,key_frame,pict_type,width,height",
        str(path),
    ], timeout=900)
    frames = data.get("frames", [])
    out = []
    for i, f in enumerate(frames):
        pts_time = f.get("pts_time")
        out.append({
            "frame_id": i,
            "pts": f.get("pts"),
            "pts_time": float(pts_time) if pts_time not in (None, "N/A") else None,
            "duration_time": float(f["duration_time"]) if f.get("duration_time") not in (None, "N/A") else None,
            "key_frame": int(f.get("key_frame", 0)),
            "pict_type": f.get("pict_type"),
            "width": f.get("width"),
            "height": f.get("height"),
        })
    return out


def count_frames(path: Path) -> int | None:
    """Decoded frame count via -count_frames. None when the stream cannot be counted."""
    try:
        data = _ffprobe(["-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", str(path)], timeout=900)
    except ProbeError:
        return None
    streams = data.get("streams") or []
    val = streams[0].get("nb_read_frames") if streams else None
    return int(val) if val and str(val).isdigit() else None


def is_vfr(index: list[dict[str, Any]]) -> bool:
    durations = {round(f["duration_time"], 6) for f in index if f.get("duration_time") is not None}
    return len(durations) > 1
