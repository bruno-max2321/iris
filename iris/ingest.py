"""Stage A: register a reference from a URL, a direct download link or a local file.

URL first (yt-dlp, no re-encode, dedicated-account cookies when present), direct link second (curl),
local file third. The original stays on this machine. Ingest is idempotent on content hash."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__, paths, probe, registry
from .store import Store, now_iso, sha256_file

RIGHTS = ("study", "own", "licensed")
PLATFORM_HOSTS = {
    "instagram.com": "instagram", "www.instagram.com": "instagram",
    "tiktok.com": "tiktok", "www.tiktok.com": "tiktok", "vm.tiktok.com": "tiktok",
    "youtube.com": "youtube", "www.youtube.com": "youtube", "youtu.be": "youtube",
}
MAX_DOWNLOADS_PER_DAY = 30
MIN_SECONDS_BETWEEN_DOWNLOADS = 60
YTDLP_FORMAT = "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best"


class IngestError(RuntimeError):
    def __init__(self, message: str, code: str = "input_unavailable") -> None:
        super().__init__(message)
        self.code = code


def _is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), re.I))


def _platform(url: str) -> str | None:
    return PLATFORM_HOSTS.get(urlparse(url).hostname or "")


def _cookies_path() -> Path | None:
    p = paths.runtime_dirs()["secrets"] / "cookies.txt"
    return p if p.exists() else None


def _enforce_download_limits(store: Store) -> None:
    if store.downloads_last_24h() >= MAX_DOWNLOADS_PER_DAY:
        raise IngestError(f"download limit reached ({MAX_DOWNLOADS_PER_DAY}/24h)", "budget_exhausted")
    since = store.seconds_since_last_download()
    if since is not None and since < MIN_SECONDS_BETWEEN_DOWNLOADS:
        raise IngestError(f"wait {int(MIN_SECONDS_BETWEEN_DOWNLOADS - since)} s before the next download", "locked")


def _download_ytdlp(url: str, tmp: Path, store: Store) -> tuple[Path, dict[str, Any]]:
    exe = shutil.which("yt-dlp")
    if not exe:
        raise IngestError("yt-dlp not installed; URL ingest unavailable")
    _enforce_download_limits(store)
    cmd = [exe, "--no-playlist", "--no-progress", "--print-json", "-f", YTDLP_FORMAT, "--merge-output-format", "mp4",
           "-o", str(tmp / "%(id)s.%(ext)s"), url]
    cookies = _cookies_path()
    if cookies:
        cmd[1:1] = ["--cookies", str(cookies)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    ok = p.returncode == 0
    store.record_download(url, ok, None if ok else (p.stderr or "")[-300:])
    if not ok:
        hint = " (sign-in or cookies required?)" if re.search(r"login|cookies|sign in|bot", p.stderr or "", re.I) else ""
        raise IngestError(f"yt-dlp failed{hint}: {(p.stderr or '').strip()[-300:]}")
    meta: dict[str, Any] = {}
    for line in (p.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                meta = json.loads(line)
            except json.JSONDecodeError:
                continue
    files = sorted(tmp.glob("*.mp4")) or sorted(tmp.glob("*"))
    if not files:
        raise IngestError("yt-dlp reported success but no file was written")
    return files[0], {
        "platform": _platform(url) or meta.get("extractor_key"),
        "webpage_url": meta.get("webpage_url", url),
        "id": meta.get("id"),
        "title": meta.get("title"),
        "uploader": meta.get("uploader") or meta.get("channel"),
        "uploader_id": meta.get("uploader_id"),
        "upload_date": meta.get("upload_date"),
        "format_id": meta.get("format_id"),
        "duration_declared_s": meta.get("duration"),
        "ytdlp_version": _ytdlp_version(exe),
    }


def _ytdlp_version(exe: str) -> str | None:
    try:
        return subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):  # pragma: no cover
        return None


def _download_direct(url: str, tmp: Path, store: Store) -> tuple[Path, dict[str, Any]]:
    _enforce_download_limits(store)
    out = tmp / "download.bin"
    p = subprocess.run(["curl", "-L", "--fail", "--silent", "--show-error", "--max-time", "900", "-o", str(out), url],
                       capture_output=True, text=True)
    ok = p.returncode == 0 and out.exists() and out.stat().st_size > 0
    store.record_download(url, ok, None if ok else (p.stderr or "")[-300:])
    if not ok:
        raise IngestError(f"direct download failed: {(p.stderr or '').strip()[-300:]}")
    return out, {"platform": "direct", "webpage_url": url}


def ingest(source: str, rights: str, *, copy_local: bool = False, workspace: Path | None = None) -> dict[str, Any]:
    if rights not in RIGHTS:
        raise IngestError(f"rights must be one of {RIGHTS}", "usage")
    store = Store(workspace)
    try:
        tmpdir = Path(tempfile.mkdtemp(prefix="iris-ingest-", dir=str(store.workspace)))
        try:
            if _is_url(source):
                if _platform(source):
                    file, src_meta = _download_ytdlp(source, tmpdir, store)
                else:
                    try:
                        file, src_meta = _download_ytdlp(source, tmpdir, store)
                    except IngestError:
                        file, src_meta = _download_direct(source, tmpdir, store)
                source_kind = "url"
            else:
                file = Path(source).expanduser().resolve()
                if not file.is_file():
                    raise IngestError(f"file not found: {file}")
                src_meta = {"platform": "local"}
                source_kind = "file"

            sha = sha256_file(file)
            asset_id = "ref_" + sha[:12]
            existing = store.get_asset_by_sha(sha)
            if existing:
                manifest = json.loads(Path(existing["manifest_path"]).read_text(encoding="utf-8"))
                return {"asset_id": existing["asset_id"], "created": False, "manifest": manifest}

            ref_dir = store.workspace / "refs" / asset_id
            ref_dir.mkdir(parents=True, exist_ok=True)
            if source_kind == "url" or copy_local:
                dest = ref_dir / ("source" + (file.suffix or ".mp4"))
                shutil.move(str(file), str(dest))
                stored_path = dest
            else:
                stored_path = file
                (ref_dir / "source.ref.json").write_text(json.dumps({"path": str(file), "sha256": sha}, indent=2), encoding="utf-8")

            readable = True
            probe_summary: dict[str, Any] | None = None
            probe_error = None
            try:
                probe_summary = probe.summarize(probe.probe_container(stored_path))
            except probe.ProbeError as exc:
                readable = False
                probe_error = str(exc)

            manifest = {
                "schema_version": "1.0.0",
                "asset_id": asset_id,
                "sha256": sha,
                "bytes": stored_path.stat().st_size,
                "stored_path": str(stored_path),
                "source": {"kind": source_kind, "input": source, **src_meta},
                "rights": rights,
                "readable": readable,
                "probe_error": probe_error,
                "probe": probe_summary,
                "created_at": now_iso(),
                "iris_version": __version__,
                "vocabulary_version": registry.vocabulary_version(),
            }
            manifest_path = ref_dir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            store.insert_asset({
                "asset_id": asset_id, "sha256": sha, "bytes": manifest["bytes"], "source_kind": source_kind,
                "source_url": source if source_kind == "url" else None,
                "source_path": str(stored_path), "rights": rights, "readable": int(readable),
                "manifest_path": str(manifest_path), "created_at": manifest["created_at"],
            })
            return {"asset_id": asset_id, "created": True, "manifest": manifest}
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    finally:
        store.close()


def load_manifest(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or paths.workspace_root()
    p = ws / "refs" / asset_id / "manifest.json"
    if not p.exists():
        raise IngestError(f"unknown asset {asset_id}", "usage")
    return json.loads(p.read_text(encoding="utf-8"))


def source_path(manifest: dict[str, Any]) -> Path:
    p = Path(manifest["stored_path"])
    if not p.exists():
        raise IngestError(f"source file missing: {p}")
    if os.environ.get("IRIS_VERIFY_SOURCE", "1") == "1" and sha256_file(p) != manifest["sha256"]:
        raise IngestError("source file changed since ingest (hash mismatch)", "validation")
    return p
