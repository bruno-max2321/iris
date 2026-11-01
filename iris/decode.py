"""Stage B helper: bounded decoding through ffmpeg rawvideo, presentation order, no frame dropped.

`-fps_mode passthrough` keeps every presented frame (VFR and duplicates included). The caller pairs the
decoded frames with the ffprobe frame index; a count mismatch is a coverage defect, never silently
ignored. ffmpeg autorotates by display matrix, so output dimensions follow the display size."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterator

import numpy as np


class DecodeError(RuntimeError):
    pass


def analysis_size(display_w: int, display_h: int, width: int) -> tuple[int, int]:
    """Scale to `width` keeping aspect; even dimensions."""
    if display_w <= 0 or display_h <= 0:
        raise DecodeError("invalid display dimensions")
    w = max(16, width - (width % 2))
    h = int(round(display_h * w / display_w))
    h -= h % 2
    return w, max(2, h)


def iter_frames(path: Path, width: int, height: int, threads: int = 2) -> Iterator[np.ndarray]:
    """Yield RGB uint8 arrays (height, width, 3). Stops at a short read (truncated stream)."""
    exe = shutil.which("ffmpeg")
    if not exe:
        raise DecodeError("ffmpeg not found on PATH")
    cmd = [
        exe, "-nostdin", "-loglevel", "error", "-threads", str(threads),
        "-i", str(path),
        "-fps_mode", "passthrough",
        "-an", "-sn",
        "-vf", f"scale={width}:{height}:flags=area",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    frame_bytes = width * height * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3)
    finally:
        try:
            proc.stdout.close()
        finally:
            proc.wait(timeout=60)
    # stderr is read after exit; a non-zero code with frames already yielded means a partial stream
    err = (proc.stderr.read().decode("utf-8", "ignore") if proc.stderr else "").strip()
    if proc.returncode not in (0, None) and err:
        raise DecodeError(err[-400:])


def pick_frames_iter(path: Path, frame_ids: list[int], width: int, height: int) -> Iterator[tuple[int, np.ndarray]]:
    """Yield (frame_id, rgb) for exactly the requested presented frames, in order, from one decode pass.
    Memory stays bounded: the caller consumes each frame before the next is decoded."""
    wanted = set(frame_ids)
    if not wanted:
        return
    last = max(wanted)
    for i, rgb in enumerate(iter_frames(path, width, height)):
        if i in wanted:
            yield i, rgb.copy()
        if i >= last:
            break


def pick_frames(path: Path, frame_ids: list[int], width: int, height: int) -> tuple[dict[int, np.ndarray], str | None]:
    """Return exactly the requested presented frames (by position in presentation order) as RGB arrays.

    One streaming decode pass; no ffmpeg `select` expression. ffmpeg's expression parser fails with
    "Cannot allocate memory" past roughly 300 `eq(n,i)` terms, and the failure used to be swallowed.
    The second element names the frame ids that were not reached (short stream), or None."""
    wanted = set(frame_ids)
    out: dict[int, np.ndarray] = dict(pick_frames_iter(path, frame_ids, width, height))
    missing = sorted(wanted - out.keys())
    return out, (f"{len(missing)} of {len(wanted)} requested frames not reached (first missing {missing[0]})" if missing else None)
