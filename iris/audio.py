"""Stage H: loudness, silences, onsets and cut-to-onset alignment with ffmpeg and numpy; transcript
with faster-whisper when installed. Absent audio is a reported state, not a failure."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

METHOD_VERSION = "audio@0.3.1"


def _ffmpeg(args: list[str], timeout: int = 900) -> tuple[int, str]:
    exe = shutil.which("ffmpeg")
    p = subprocess.run([exe or "ffmpeg", "-nostdin", "-hide_banner", "-nostats", *args], capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stderr or "") + (p.stdout or "")


def loudness(src: Path) -> dict[str, Any]:
    rc, out = _ffmpeg(["-i", str(src), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    # ebur128 logs one progress line per 100 ms ("I: -70.0 LUFS" while gated) before the final Summary
    # block. Only the Summary carries the programme values, so everything before it is discarded.
    summary = out[out.rfind("Summary:"):] if "Summary:" in out else ""

    def grab(pattern: str) -> float | None:
        m = re.search(pattern, summary)
        return float(m.group(1)) if m else None

    return {
        "integrated_lufs": grab(r"\n\s*I:\s*(-?[\d.]+) LUFS"),
        "lra_lu": grab(r"\n\s*LRA:\s*(-?[\d.]+) LU"),
        "true_peak_dbtp": grab(r"Peak:\s*(-?[\d.]+) dBFS"),
        "threshold_lufs": grab(r"Integrated loudness:\s*\n\s*I:[^\n]*\n\s*Threshold:\s*(-?[\d.]+) LUFS"),
        "method": "ffmpeg ebur128=peak=true (summary block)",
        "ok": rc == 0 and bool(summary),
    }


def loudness_crosscheck(src: Path) -> dict[str, Any]:
    """Independent read of the same programme through loudnorm's measurement pass (used by tests)."""
    import json as _json

    rc, out = _ffmpeg(["-i", str(src), "-vn", "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    i, j = out.rfind("{"), out.rfind("}")
    if rc != 0 or i < 0 or j < i:
        return {"ok": False}
    d = _json.loads(out[i:j + 1])
    return {"ok": True, "integrated_lufs": float(d["input_i"]), "lra_lu": float(d["input_lra"]), "true_peak_dbtp": float(d["input_tp"])}


def silences(src: Path, noise_db: float = -35.0, min_s: float = 0.3) -> list[dict[str, float]]:
    rc, out = _ffmpeg(["-i", str(src), "-vn", "-af", f"silencedetect=n={noise_db}dB:d={min_s}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", out)]
    ends = re.findall(r"silence_end:\s*(-?[\d.]+)\s*\|\s*silence_duration:\s*(-?[\d.]+)", out)
    res = []
    for i, s in enumerate(starts):
        if i < len(ends):
            res.append({"start_s": s, "end_s": float(ends[i][0]), "duration_s": float(ends[i][1])})
        else:
            res.append({"start_s": s, "end_s": None, "duration_s": None})
    return res


def pcm_mono(src: Path, sr: int = 16000) -> np.ndarray | None:
    exe = shutil.which("ffmpeg") or "ffmpeg"
    p = subprocess.run([exe, "-nostdin", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                       capture_output=True, timeout=900)
    if p.returncode != 0 or not p.stdout:
        return None
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def onsets(y: np.ndarray, sr: int = 16000, n_fft: int = 1024, hop: int = 512, min_gap_s: float = 0.1) -> tuple[list[float], dict[str, Any]]:
    """Spectral-flux onset times (s). Numpy only; librosa, when present, could replace this."""
    if y.size < n_fft * 2:
        return [], {"frames": 0}
    win = np.hanning(n_fft).astype(np.float32)
    n_frames = 1 + (len(y) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    spec = np.abs(np.fft.rfft(y[idx] * win, axis=1))
    flux = np.maximum(0.0, np.diff(np.log1p(spec), axis=0)).sum(axis=1)
    flux = np.concatenate([[0.0], flux])
    med = np.median(flux); mad = np.median(np.abs(flux - med)) * 1.4826 + 1e-9
    thr = med + 3.0 * mad
    min_gap = max(1, int(min_gap_s * sr / hop))
    picks = []
    last = -min_gap
    for i in range(1, len(flux) - 1):
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1] and i - last >= min_gap:
            picks.append(i); last = i
    times = [round(float(i * hop / sr), 4) for i in picks]
    return times, {"frames": int(n_frames), "threshold": float(thr), "median_flux": float(med)}


def speech_music_split(y: np.ndarray, sr: int = 16000) -> dict[str, Any]:
    """Coarse activity segmentation by RMS energy in 50 ms windows; not speech/music classification."""
    hop = int(0.05 * sr)
    n = len(y) // hop
    if n == 0:
        return {"active_share": None}
    rms = np.sqrt((y[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    thr = max(1e-4, float(np.percentile(rms, 20)) * 3)
    return {"active_share": round(float((rms > thr).mean()), 4), "rms_p50": float(np.percentile(rms, 50)), "method": "rms_activity_50ms"}


def transcript(y: np.ndarray | None, sr: int = 16000, workdir: Path | None = None) -> dict[str, Any]:
    """faster-whisper in a supervised child process on the PCM ffmpeg already decoded.

    The child keeps CTranslate2's thread runtime away from PaddlePaddle's (sharing one interpreter made
    whisper 35x slower on the VM) and PyAV is never touched. Budgets: model load and first segment within
    IRIS_WHISPER_FIRST_BUDGET_S (first run downloads the model), then a stall budget between segments."""
    import importlib.util
    import os
    import tempfile

    from . import worker

    if importlib.util.find_spec("faster_whisper") is None:
        return {"status": "skipped", "reason": "faster-whisper not installed"}
    if y is None or y.size < sr // 2:
        return {"status": "skipped", "reason": "no decodable PCM"}
    duration = y.size / sr
    workdir = Path(workdir or tempfile.mkdtemp(prefix="iris-whisper-"))
    workdir.mkdir(parents=True, exist_ok=True)
    pcm = workdir / "pcm16k.npy"
    np.save(pcm, y.astype(np.float32))
    first = float(os.environ.get("IRIS_WHISPER_FIRST_BUDGET_S", "900"))
    stall = float(os.environ.get("IRIS_WHISPER_STALL_BUDGET_S", "120"))
    total = first + max(120.0, 6.0 * duration)
    r = worker.run_worker("whisper", {"pcm": str(pcm), "model": os.environ.get("IRIS_WHISPER_MODEL", "small")},
                          first_budget_s=first, stall_budget_s=stall, total_budget_s=total, workdir=workdir)
    try:
        pcm.unlink(missing_ok=True)
    except OSError:
        pass
    res = r.get("result") or {}
    if r["killed"]:
        return {"status": "failed", "reason": f"whisper worker killed ({r['killed']} budget) after {r['elapsed_s']} s",
                "elapsed_s": r["elapsed_s"]}
    if r["exit"] not in (0, None) or res.get("status") != "ok":
        reason = res.get("reason") or (r["stderr_tail"].strip().splitlines() or ["worker exited"])[-1][:240]
        return {"status": "failed", "reason": f"whisper worker failed: {reason}", "elapsed_s": r["elapsed_s"]}
    res["elapsed_s"] = r["elapsed_s"]
    return res


def run(src: Path, has_audio: bool, cut_times_s: list[float], workdir: Path | None = None) -> dict[str, Any]:
    if not has_audio:
        return {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "status": "absent", "reason": "no audio stream"}
    import time

    timing: dict[str, float] = {}
    t = time.time(); loud = loudness(src); timing["loudness_s"] = round(time.time() - t, 3)
    t = time.time(); sil = silences(src); timing["silences_s"] = round(time.time() - t, 3)
    t = time.time(); y = pcm_mono(src); timing["pcm_s"] = round(time.time() - t, 3)
    t = time.time(); ons, ons_meta = ([], {}) if y is None else onsets(y); timing["onsets_s"] = round(time.time() - t, 3)
    near = 0
    if ons and cut_times_s:
        arr = np.array(ons)
        for c in cut_times_s:
            if np.min(np.abs(arr - c)) <= 0.040:
                near += 1
    t = time.time(); tr = transcript(y, workdir=workdir); timing["transcript_s"] = round(time.time() - t, 3)
    return {
        "schema_version": "1.0.0", "method_version": METHOD_VERSION, "status": "ok",
        "loudness": loud, "silences": sil, "silence_count": len(sil),
        "onsets_s": ons, "onset_count": len(ons), "onset_meta": ons_meta,
        "cuts_within_40ms_of_onset": near, "cuts_total": len(cut_times_s),
        "share_of_cuts_on_onset": round(near / len(cut_times_s), 3) if cut_times_s else None,
        "activity": None if y is None else speech_music_split(y),
        "transcript": tr,
        "timing": timing,
    }
