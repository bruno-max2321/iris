"""`iris analyze`: stages B (index) and C (measure) for milestone 1, with coverage accounting,
idempotent job keys, a heavy-job lock and per-stage checkpoints so a restart resumes."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from . import __version__, decode, frames_io, ingest, measure, probe
from .store import Store, job_key, now_iso

PIPELINE_VERSION = "m1.0"
ANALYSIS_WIDTH = 320
STAGES_M1 = ["index", "measure"]


class AnalyzeError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _write(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def stage_index(src: Path, ref_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    out = ref_dir / "index.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    t0 = time.time()
    frames = probe.frame_index(src)
    counted = probe.count_frames(src)
    vid = (manifest.get("probe") or {}).get("video") or {}
    idx = {
        "schema_version": "1.0.0",
        "asset_id": manifest["asset_id"],
        "frame_count": len(frames),
        "nb_read_frames": counted,
        "nb_frames_declared": vid.get("nb_frames_declared"),
        "nominal_fps": vid.get("nominal_fps"),
        "time_base": vid.get("time_base"),
        "vfr": probe.is_vfr(frames),
        "first_pts_time": frames[0]["pts_time"] if frames else None,
        "last_pts_time": frames[-1]["pts_time"] if frames else None,
        "missing_pts": sum(1 for f in frames if f["pts_time"] is None),
        "elapsed_s": round(time.time() - t0, 3),
        "frames": frames,
    }
    _write(out, idx)
    return idx


def stage_measure(src: Path, ref_dir: Path, manifest: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    marker = ref_dir / "measure.done.json"
    if marker.exists():
        return json.loads(marker.read_text(encoding="utf-8"))
    vid = (manifest.get("probe") or {}).get("video") or {}
    w, h = decode.analysis_size(int(vid.get("display_width") or 0), int(vid.get("display_height") or 0), ANALYSIS_WIDTH)
    meas = measure.FrameMeasurer(w, h, int(vid.get("display_height") or h))
    rows: list[dict[str, Any]] = []
    t0 = time.time()
    decode_error = None
    try:
        for i, frame in enumerate(decode.iter_frames(src, w, h)):
            rows.append(meas.measure(i, frame))
    except decode.DecodeError as exc:
        decode_error = str(exc)
    path, fmt = frames_io.write_frames(rows, ref_dir, measure.COLUMNS)
    result = {
        "rows": len(rows), "decoded_frames": len(rows), "format": fmt, "path": path.name,
        "transform": meas.transform(), "decode_error": decode_error,
        "elapsed_s": round(time.time() - t0, 3),
        "frames_per_s": round(len(rows) / max(1e-6, time.time() - t0), 1),
    }
    _write(marker, result)
    return result


def build_coverage(manifest: dict[str, Any], index: dict[str, Any] | None, meas: dict[str, Any] | None,
                   index_error: str | None) -> dict[str, Any]:
    reasons: list[str] = []
    if index is None:
        decode_status = "partial"
        reasons.append(f"frame index unavailable: {index_error}")
        expected = None
        decoded = 0
    else:
        expected = index["frame_count"]
        decoded = meas["decoded_frames"] if meas else 0
        decode_status = "full"
        if index.get("nb_read_frames") not in (None, expected):
            decode_status = "partial"
            reasons.append(f"ffprobe counted {index['nb_read_frames']} frames but indexed {expected}")
        if meas is None or decoded != expected:
            decode_status = "partial"
            reasons.append(f"decoded {decoded} of {expected} indexed frames")
        if index.get("missing_pts"):
            reasons.append(f"{index['missing_pts']} frames without PTS")
        # a stream shorter than its own declaration is a truncated or damaged file
        declared = index.get("nb_frames_declared")
        if declared and declared > expected:
            decode_status = "partial"
            reasons.append(f"stream declares {declared} frames but only {expected} are present")
        vid = (manifest.get("probe") or {}).get("video") or {}
        declared_dur = vid.get("duration_s") or manifest.get("probe", {}).get("duration_s")
        last = index.get("last_pts_time")
        if declared_dur and last is not None and declared_dur - last > 0.5:
            decode_status = "partial"
            reasons.append(f"declared duration {declared_dur:.2f}s but last frame at {last:.2f}s")
        if meas and meas.get("decode_error"):
            reasons.append(f"decoder: {meas['decode_error']}")
    measurement_status = "full" if (meas and meas["rows"] == decoded and decoded > 0) else "partial"
    if meas and meas["rows"] != decoded:
        reasons.append(f"measured {meas['rows']} of {decoded} decoded frames")
    return {
        "schema_version": "1.0.0",
        "asset_id": manifest["asset_id"],
        "decode": decode_status,
        "measurement": measurement_status,
        "model_exposure": "none",
        "expected_frames": expected,
        "decoded_frames": decoded,
        "measured_frames": meas["rows"] if meas else 0,
        "vfr": index["vfr"] if index else None,
        "frames_format": meas["format"] if meas else None,
        "reasons": reasons,
        "pipeline_version": PIPELINE_VERSION,
        "iris_version": __version__,
        "generated_at": now_iso(),
    }


def analyze(asset_id: str, mode: str = "economy", workspace: Path | None = None) -> dict[str, Any]:
    if mode not in ("economy", "strict"):
        raise AnalyzeError("mode must be economy or strict", "usage")
    manifest = ingest.load_manifest(asset_id, workspace)
    store = Store(workspace)
    try:
        key = job_key({"sha256": manifest["sha256"], "pipeline": PIPELINE_VERSION, "measure": measure.METHOD_VERSION,
                       "width": ANALYSIS_WIDTH, "mode": mode})
        job, created = store.create_or_get_job(key, asset_id, "analyze", mode)
        if job["state"] in ("review_ready", "partial", "failed") and not created and set(STAGES_M1) <= set(job["stages_done"]):
            cov_path = store.workspace / "refs" / asset_id / "coverage.json"
            return {"job": job, "created": False, "coverage": json.loads(cov_path.read_text(encoding="utf-8")) if cov_path.exists() else None}
        ref_dir = store.workspace / "refs" / asset_id
        try:
            with store.heavy_job_lock():
                return _run_stages(store, job, manifest, ref_dir)
        except BlockingIOError:
            raise AnalyzeError("another heavy job holds the lock", "locked")
    finally:
        store.close()


def _run_stages(store: Store, job: dict[str, Any], manifest: dict[str, Any], ref_dir: Path) -> dict[str, Any]:
    index: dict[str, Any] | None = None
    meas: dict[str, Any] | None = None
    index_error: str | None = None
    try:
        src = ingest.source_path(manifest)
    except ingest.IngestError as exc:
        job = store.update_job(job["job_id"], state="failed", error=str(exc))
        raise AnalyzeError(str(exc), exc.code)

    if not manifest.get("readable"):
        index_error = manifest.get("probe_error") or "container unreadable"
    else:
        try:
            index = stage_index(src, ref_dir, manifest)
            job = store.update_job(job["job_id"], state="indexed", stage_done="index")
        except probe.ProbeError as exc:
            index_error = str(exc)

    if index is not None and index["frame_count"] > 0:
        job = store.update_job(job["job_id"], state="measuring")
        meas = stage_measure(src, ref_dir, manifest, index)
        job = store.update_job(job["job_id"], stage_done="measure")

    coverage = build_coverage(manifest, index, meas, index_error)
    _write(ref_dir / "coverage.json", coverage)
    final_state = "review_ready" if coverage["decode"] == "full" and coverage["measurement"] == "full" else "partial"
    job = store.update_job(job["job_id"], state=final_state, stage_done="coverage")
    return {"job": job, "created": True, "coverage": coverage, "index_summary": None if index is None else
            {k: index[k] for k in ("frame_count", "nb_read_frames", "vfr", "nominal_fps", "first_pts_time", "last_pts_time")},
            "measure_summary": meas}
