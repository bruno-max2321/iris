"""`iris gc [--keep-days 90] [--apply]`: the declared retention policy. Dry run unless --apply.

- Downloaded originals (refs/<id>/source.<ext> of a URL ingest) older than keep-days are deleted, unless
  the reference is in an approved Style Bible. A local file the user pointed at is never touched (it is
  only referenced), nor is a copy made with --copy.
- Before an original goes, every frame cited by an accepted or corrected claim, plus each shot's middle
  keyframe, is saved as a JPEG in refs/<id>/evidence_frames/. If that fails the original is kept: gc
  never removes evidence cited by an accepted claim.
- Stage outputs, sheets, evidence frames, interpret packets, claims and the ledger are kept indefinitely.
- Leftover temporary directories (iris-ingest-*, refs/<id>/work, iris-ocr-*, iris-regions-*) older than
  TEMP_MIN_AGE_H are removed.
It takes the heavy-job lock so it never races an analysis."""

from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import evidence, ingest, paths
from .store import Store

DEFAULT_KEEP_DAYS = 90
TEMP_MIN_AGE_H = 24
FRAME_LONG_SIDE = 960
FRAMES_DIR = "evidence_frames"


def _age_days(iso: str | None, now: float) -> float | None:
    if not iso:
        return None
    try:
        return (now - datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()) / 86400
    except ValueError:
        return None


def _approved_refs(ws: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in sorted((ws / "styles").glob("*/style_bible.json")):
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if b.get("status") == "approved":
            for aid in b.get("built_from") or []:
                out.setdefault(aid, []).append(b.get("style_id") or p.parent.name)
    return out


def frame_path(ref_dir: Path, sid: str, which: str) -> Path:
    return ref_dir / FRAMES_DIR / f"keyframe_{sid}_{which}.jpg"


def _frames_to_keep(asset_id: str, ref_dir: Path, store: Store) -> dict[str, int]:
    """file name -> frame_id for cited frames of accepted/corrected claims and every shot's mid keyframe."""
    docs = evidence.load_docs(ref_dir)
    idx = evidence.build_index(docs)
    want: dict[str, int] = {}
    for s in (docs.get("shots") or {}).get("shots") or []:
        if (s.get("keyframes") or {}).get("mid") is not None:
            want[f"keyframe:{s['shot_id']}:mid"] = int(s["keyframes"]["mid"])
    for c in store.list_claims(asset_id):
        if c["review_status"] not in ("accepted", "corrected"):
            continue
        for e in c.get("evidence_ids") or []:
            ent = idx.get(e)
            if ent and ent["kind"] == "frame":
                want[e] = int(ent["value"]["frame_id"])
    return want


def _materialize(asset_id: str, ref_dir: Path, want: dict[str, int], manifest: dict[str, Any]) -> list[str]:
    from PIL import Image

    from . import decode

    todo: dict[int, list[Path]] = {}
    for eid, fid in want.items():
        _, sid, which = eid.split(":")
        p = frame_path(ref_dir, sid, which)
        if not p.exists():
            todo.setdefault(fid, []).append(p)
    if not todo:
        return []
    vid = (manifest.get("probe") or {}).get("video") or {}
    dw, dh = int(vid.get("display_width") or 0), int(vid.get("display_height") or 0)
    scale = min(1.0, FRAME_LONG_SIDE / max(dw, dh, 1))
    w, h = max(2, int(dw * scale) // 2 * 2), max(2, int(dh * scale) // 2 * 2)
    (ref_dir / FRAMES_DIR).mkdir(exist_ok=True)
    written = []
    for fid, rgb in decode.pick_frames_iter(ingest.source_path(manifest), sorted(todo), w, h):
        for p in todo.pop(fid):
            Image.fromarray(rgb).save(p, "JPEG", quality=88)
            written.append(p.name)
    if todo:
        raise RuntimeError(f"frames not decoded: {sorted(todo)}")
    return written


def _temp_dirs(ws: Path, now: float) -> list[Path]:
    cands = list(ws.glob("iris-ingest-*"))
    for ref in (ws / "refs").glob("*"):
        cands += [ref / "work"] + list(ref.glob("iris-ocr-*")) + list(ref.glob("iris-regions-*"))
    return [p for p in cands if p.is_dir() and now - p.stat().st_mtime > TEMP_MIN_AGE_H * 3600]


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def run(keep_days: int = DEFAULT_KEEP_DAYS, apply: bool = False, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or paths.workspace_root()
    now = time.time()
    store = Store(ws)
    try:
        with store.heavy_job_lock():
            approved = _approved_refs(ws)
            originals, kept = [], []
            for mp in sorted((ws / "refs").glob("*/manifest.json")):
                m = json.loads(mp.read_text(encoding="utf-8"))
                aid, ref_dir = m["asset_id"], mp.parent
                src = Path(m.get("stored_path") or "")
                if (m.get("source") or {}).get("kind") != "url":
                    continue  # local files are only referenced; copies made with --copy are the user's choice
                if not src.exists() or src.parent != ref_dir:
                    continue  # already collected, or not ours
                age = _age_days(m.get("created_at"), now)
                row = {"asset_id": aid, "path": str(src), "bytes": src.stat().st_size, "age_days": round(age, 1) if age is not None else None}
                if aid in approved:
                    kept.append({**row, "reason": f"in approved Style Bible {', '.join(approved[aid])}"})
                elif age is None or age < keep_days:
                    kept.append({**row, "reason": f"younger than {keep_days} days"})
                else:
                    row["frames_to_keep"] = len(_frames_to_keep(aid, ref_dir, store))
                    originals.append(row)
            temps = [{"path": str(p), "bytes": _size(p)} for p in _temp_dirs(ws, now)]
            deleted, errors = [], []
            if apply:
                for row in originals:
                    ref_dir = Path(row["path"]).parent
                    try:
                        m = ingest.load_manifest(row["asset_id"], ws)
                        written = _materialize(row["asset_id"], ref_dir, _frames_to_keep(row["asset_id"], ref_dir, store), m)
                    except Exception as exc:  # keep the original when its cited frames cannot be saved
                        errors.append({"asset_id": row["asset_id"], "error": f"kept: evidence frames not saved ({exc})"})
                        continue
                    Path(row["path"]).unlink()
                    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "deleted": row["path"], "sha256": m.get("sha256"),
                           "bytes": row["bytes"], "keep_days": keep_days, "frames_saved": written}
                    with (ref_dir / "gc.jsonl").open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(rec) + "\n")
                    deleted.append({**row, "frames_saved": len(written)})
                for t in temps:
                    shutil.rmtree(t["path"], ignore_errors=True)
    finally:
        store.close()
    return {"ok": not errors, "applied": apply, "keep_days": keep_days,
            "originals_to_delete" if not apply else "originals_deleted": deleted if apply else originals,
            "originals_kept": kept, "temp_dirs": temps, "bytes_freed" if apply else "bytes_to_free":
                sum(r["bytes"] for r in (deleted if apply else originals)) + sum(t["bytes"] for t in temps),
            "errors": errors, "never_deleted": "stage outputs, evidence frames, sheets, packets, claims, review events, ledger"}
