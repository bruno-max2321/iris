"""`iris doctor`: verify the environment without mutating it.

Checks are grouped by severity. `fail` blocks production runs; `warn` is reported and allowed."""

from __future__ import annotations

import importlib
import importlib.metadata as md
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import paths

REQUIRED_PYTHON = (3, 12)
REQUIRED_FFMPEG_FILTERS = ["tile", "ebur128", "silencedetect", "blackdetect", "freezedetect", "scale"]
OPTIONAL_FFMPEG_FILTERS = ["drawtext", "subtitles", "showspectrumpic"]
STAGE_MODULES = {
    "media": ["av", "cv2", "numpy", "scenedetect", "imagehash", "pyarrow"],
    "text": ["paddleocr", "paddle", "rapidfuzz"],
    "audio": ["faster_whisper", "librosa"],
    "people": ["mediapipe"],
    "interpret": ["anthropic"],
}
MIN_FREE_GB = 15.0


def _run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover
        return 127, str(exc)


def _check(name: str, status: str, detail: Any = None) -> dict[str, Any]:
    return {"check": name, "status": status, "detail": detail}


def check_python() -> dict[str, Any]:
    v = sys.version_info[:3]
    in_venv = sys.prefix != sys.base_prefix
    status = "ok" if v[:2] >= REQUIRED_PYTHON else "warn"
    return _check("python", status, {"version": ".".join(map(str, v)), "venv": in_venv, "executable": sys.executable,
                                     "required": f">={REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}"})


def check_ffmpeg() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        if not path:
            out.append(_check(tool, "fail", "not found on PATH"))
            continue
        rc, text = _run([tool, "-version"])
        version = text.splitlines()[0] if text else ""
        out.append(_check(tool, "ok" if rc == 0 else "fail", {"path": path, "version": version}))
    if shutil.which("ffmpeg"):
        rc, text = _run(["ffmpeg", "-hide_banner", "-filters"])
        present = {line.split()[1] for line in text.splitlines() if len(line.split()) > 1 and line.strip()[:1] in ".TSC"}
        missing_req = [f for f in REQUIRED_FFMPEG_FILTERS if f not in present]
        missing_opt = [f for f in OPTIONAL_FFMPEG_FILTERS if f not in present]
        out.append(_check("ffmpeg.filters.required", "fail" if missing_req else "ok", {"missing": missing_req}))
        out.append(_check("ffmpeg.filters.optional", "warn" if missing_opt else "ok",
                          {"missing": missing_opt, "note": "drawtext needs libfreetype; without it contact sheets use fixed time per sheet"}))
    return out


def check_ytdlp() -> dict[str, Any]:
    path = shutil.which("yt-dlp")
    if not path:
        return _check("yt-dlp", "warn", "not found; URL ingest unavailable, file ingest still works")
    rc, text = _run(["yt-dlp", "--version"])
    return _check("yt-dlp", "ok" if rc == 0 else "warn", {"path": path, "version": text.strip()})


def check_modules() -> list[dict[str, Any]]:
    out = []
    for stage, mods in STAGE_MODULES.items():
        missing = []
        for m in mods:
            try:
                importlib.import_module(m)
            except Exception:  # noqa: BLE001 - any import failure counts as missing
                missing.append(m)
        out.append(_check(f"modules.{stage}", "ok" if not missing else "warn", {"missing": missing}))
    return out


def check_opencv_variants() -> dict[str, Any]:
    names = sorted({d.metadata["Name"] for d in md.distributions() if d.metadata["Name"].lower().startswith("opencv")})
    status = "ok" if len(names) <= 1 else "fail"
    return _check("opencv.single_variant", status, {"installed": names, "expected": ["opencv-python-headless"]})


def check_registry() -> dict[str, Any]:
    try:
        from . import registry

        vocab = registry.load_vocabulary()
        n_terms = sum(len(d["terms"]) for d in vocab["dimensions"])
        return _check("registry", "ok", {"version": vocab["version"], "dimensions": len(vocab["dimensions"]), "terms": n_terms,
                                         "path": str(paths.VOCABULARY_FILE)})
    except Exception as exc:  # noqa: BLE001
        return _check("registry", "fail", str(exc))


def check_schemas() -> dict[str, Any]:
    try:
        import jsonschema

        schema = json.loads(paths.STYLE_BIBLE_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        example = json.loads(paths.STYLE_BIBLE_EXAMPLE.read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft202012Validator(schema).iter_errors(example))
        return _check("schemas.style_bible", "ok" if not errors else "fail", {"example_errors": len(errors)})
    except Exception as exc:  # noqa: BLE001
        return _check("schemas.style_bible", "fail", str(exc))


def check_secrets() -> dict[str, Any]:
    d = paths.runtime_dirs()["secrets"]
    if not d.exists():
        return _check("secrets", "warn", {"path": str(d), "note": "missing; interpret run and URL ingest with cookies will be unavailable"})
    problems = []
    for p in d.iterdir():
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode & 0o077:
            problems.append({"file": p.name, "mode": oct(mode)})
    dmode = stat.S_IMODE(d.stat().st_mode)
    if dmode & 0o077:
        problems.append({"dir": str(d), "mode": oct(dmode)})
    return _check("secrets.permissions", "fail" if problems else "ok",
                  {"path": str(d), "problems": problems, "has_anthropic_key": (d / "anthropic.key").exists(),
                   "has_cookies": (d / "cookies.txt").exists()})


def check_disk() -> dict[str, Any]:
    w = paths.workspace_root()
    probe_dir = w
    while not probe_dir.exists() and probe_dir.parent != probe_dir:
        probe_dir = probe_dir.parent
    usage = shutil.disk_usage(probe_dir)
    free_gb = usage.free / 1e9
    return _check("disk.free", "ok" if free_gb >= MIN_FREE_GB else "fail",
                  {"workspace": str(w), "free_gb": round(free_gb, 1), "min_free_gb": MIN_FREE_GB})


def check_host() -> dict[str, Any]:
    return _check("host", "ok", {"system": platform.system(), "release": platform.release(), "machine": platform.machine(),
                                 "cpu_count": os.cpu_count()})


def run() -> dict[str, Any]:
    checks: list[dict[str, Any]] = [check_host(), check_python()]
    checks += check_ffmpeg()
    checks.append(check_ytdlp())
    checks += check_modules()
    checks.append(check_opencv_variants())
    checks.append(check_registry())
    checks.append(check_schemas())
    checks.append(check_secrets())
    checks.append(check_disk())
    worst = "ok"
    for c in checks:
        if c["status"] == "fail":
            worst = "fail"
            break
        if c["status"] == "warn":
            worst = "warn"
    return {"ok": worst != "fail", "status": worst, "checks": checks, "workspace": str(paths.workspace_root())}
