"""`iris analyze`: stages B–I with coverage accounting, idempotent job keys, a heavy-job lock and
per-stage checkpoints so a restart resumes.

Milestone 1: index, measure. Milestone 2: shots, motion, text, regions, audio, sheets. Every stage
after `measure` records `ok | skipped | failed` with a reason in coverage.json; a skipped optional
stage never counts as success."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import json
import shutil
import time
import traceback
from pathlib import Path
from typing import Any

from . import __version__, decode, frames_io, ingest, measure, probe
from .store import Store, job_key, now_iso

PIPELINE_VERSION = "m2.1"
ANALYSIS_WIDTH = 320
CORE_STAGES = ["index", "measure"]
DERIVED_STAGES = ["shots", "motion", "text", "regions", "audio", "sheets"]
# stages whose checkpoints must be dropped when a stage is forced (they consume its output)
DERIVED_DEPENDENTS = {"shots": ["motion", "text", "regions", "audio", "sheets"], "text": ["regions", "sheets"],
                      "regions": ["sheets"], "motion": [], "audio": [], "sheets": []}


class AnalyzeError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _write(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------------------------------ stages
def stage_index(src: Path, ref_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    out = ref_dir / "index.json"
    if out.exists():
        return _read(out)
    t0 = time.time()
    frames = probe.frame_index(src)
    counted = probe.count_frames(src)
    vid = (manifest.get("probe") or {}).get("video") or {}
    idx = {
        "schema_version": "1.0.0", "asset_id": manifest["asset_id"],
        "frame_count": len(frames), "nb_read_frames": counted, "nb_frames_declared": vid.get("nb_frames_declared"),
        "nominal_fps": vid.get("nominal_fps"), "time_base": vid.get("time_base"), "vfr": probe.is_vfr(frames),
        "first_pts_time": frames[0]["pts_time"] if frames else None, "last_pts_time": frames[-1]["pts_time"] if frames else None,
        "missing_pts": sum(1 for f in frames if f["pts_time"] is None), "elapsed_s": round(time.time() - t0, 3), "frames": frames,
    }
    _write(out, idx)
    return idx


def stage_measure(src: Path, ref_dir: Path, manifest: dict[str, Any], index: dict[str, Any]) -> dict[str, Any]:
    marker = ref_dir / "measure.done.json"
    if marker.exists():
        return _read(marker)
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
    result = {"rows": len(rows), "decoded_frames": len(rows), "format": fmt, "path": path.name, "transform": meas.transform(),
              "decode_error": decode_error, "elapsed_s": round(time.time() - t0, 3),
              "frames_per_s": round(len(rows) / max(1e-6, time.time() - t0), 1)}
    _write(marker, result)
    return result


STAGE_OUTPUTS = {"shots": ["shots.json", "events.json"], "motion": ["motion.json"], "text": ["text.json"],
                 "regions": ["color.json"], "audio": ["audio.json"], "sheets": ["sheets.json"]}


def _derived(ref_dir: Path, name: str, fn, *, mode: str) -> dict[str, Any]:
    """Run a derived stage with a checkpoint; never raise, always return a status record.

    A recompute that fails (or is skipped) must not destroy an earlier good output: the previous files
    are snapshotted first and restored on failure, and the record says so (`kept_previous_output`)."""
    marker = ref_dir / f"{name}.done.json"
    if marker.exists():
        rec = _read(marker)
        if rec.get("status") in ("ok", "absent"):
            rec["cached"] = True
            return rec
        # failed or skipped stages are retried on resume: the environment may have been repaired
    previous: dict[str, bytes] = {}
    prev_ok = False
    for out_name in STAGE_OUTPUTS.get(name, []):
        p = ref_dir / out_name
        if p.exists():
            previous[out_name] = p.read_bytes()
            try:
                prev_ok = prev_ok or json.loads(previous[out_name]).get("status", "ok") in ("ok", "absent")
            except (json.JSONDecodeError, AttributeError):
                pass
    t0 = time.time()
    try:
        summary = fn()
        status = summary.pop("_status", "ok") if isinstance(summary, dict) else "ok"
        rec = {"stage": name, "status": status, "elapsed_s": round(time.time() - t0, 3), "mode": mode, "summary": summary}
    except Exception as exc:  # noqa: BLE001 - a derived stage failing must not kill the job
        rec = {"stage": name, "status": "failed", "elapsed_s": round(time.time() - t0, 3), "mode": mode,
               "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-1200:]}
    if rec["status"] in ("failed", "skipped") and prev_ok:
        for out_name, data in previous.items():
            (ref_dir / out_name).write_bytes(data)
        rec["kept_previous_output"] = True
        rec["note"] = "recompute failed; the previous ok output was restored and downstream stages keep using it"
    _write(marker, rec)
    return rec


def run_derived_stages(src: Path, ref_dir: Path, manifest: dict[str, Any], index: dict[str, Any], mode: str) -> dict[str, dict[str, Any]]:
    from . import audio, motion, regions, sheets, shots, textocr

    vid = (manifest.get("probe") or {}).get("video") or {}
    dw, dh = int(vid.get("display_width") or 0), int(vid.get("display_height") or 0)
    fps = float(index.get("nominal_fps") or 30.0)
    frames = frames_io.read_frames(ref_dir)
    records: dict[str, dict[str, Any]] = {}

    def do_shots():
        shots_doc, events_doc = shots.detect(frames, index)
        _write(ref_dir / "shots.json", shots_doc)
        _write(ref_dir / "events.json", events_doc)
        return {"shots": shots_doc["montage"]["shot_count"], "cuts": shots_doc["montage"]["cut_count"],
                "events": events_doc["counts"], "cuts_per_s": shots_doc["montage"]["cuts_per_s"]}
    records["shots"] = _derived(ref_dir, "shots", do_shots, mode=mode)
    shots_doc = _read(ref_dir / "shots.json") if (ref_dir / "shots.json").exists() else {"shots": [], "cut_times_s": []}
    shot_list = shots_doc.get("shots", [])
    work = ref_dir / "work"
    work.mkdir(exist_ok=True)

    def do_motion():
        doc = motion.run(src, dw, dh, shot_list, frames, fps)
        _write(ref_dir / "motion.json", doc)
        classes: dict[str, int] = {}
        for s in doc["shots"]:
            classes[s.get("class", "unclear")] = classes.get(s.get("class", "unclear"), 0) + 1
        return {"pairs": doc["pairs"], "classes": classes}

    def do_text():
        doc = textocr.run(src, ref_dir, shot_list, index["frame_count"], dw, dh, index["frames"], mode=mode)
        _write(ref_dir / "text.json", doc)
        return {"_status": doc.get("status", "ok"), "backend": doc.get("backend"), "reason": doc.get("reason"),
                "seconds_per_frame": doc.get("seconds_per_frame"), "sampled_frames": doc.get("sampled_frames"),
                "frames_ocr": doc.get("frames_ocr"), "frames_reused": doc.get("frames_reused"),
                "frames_timed_out": len(doc.get("frames_timed_out") or []), "timing": doc.get("timing"),
                "tracks": len(doc.get("tracks", []))}

    def do_audio():
        has_audio = bool((manifest.get("probe") or {}).get("audio"))
        doc = audio.run(src, has_audio, shots_doc.get("cut_times_s", []), workdir=work / "whisper")
        _write(ref_dir / "audio.json", doc)
        return {"_status": "absent" if doc.get("status") == "absent" else "ok",
                "lufs": (doc.get("loudness") or {}).get("integrated_lufs"), "onsets": doc.get("onset_count"),
                "share_of_cuts_on_onset": doc.get("share_of_cuts_on_onset"), "transcript": (doc.get("transcript") or {}).get("status"),
                "timing": doc.get("timing")}

    # motion (numpy, in-process), text (OCR child process) and audio (ffmpeg + whisper child process) are
    # independent once shots exist; they run concurrently and wall time is bounded by the slowest one.
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="iris-stage") as pool:
        futures = {
            "motion": pool.submit(_derived, ref_dir, "motion", do_motion, mode=mode),
            "text": pool.submit(_derived, ref_dir, "text", do_text, mode=mode),
            "audio": pool.submit(_derived, ref_dir, "audio", do_audio, mode=mode),
        }
        for name, fut in futures.items():
            records[name] = fut.result()
    text_doc = _read(ref_dir / "text.json") if (ref_dir / "text.json").exists() else {"tracks": []}

    def do_regions():
        doc = regions.run(src, ref_dir, shot_list, dw, dh, text_doc.get("tracks"))
        _write(ref_dir / "color.json", doc)
        return {"shots": sum(1 for s in doc["shots"] if s.get("status") == "ok"), "summary": doc["summary"]}
    records["regions"] = _derived(ref_dir, "regions", do_regions, mode=mode)

    def do_sheets():
        color_doc = _read(ref_dir / "color.json") if (ref_dir / "color.json").exists() else None
        doc = sheets.run(src, ref_dir, shot_list, frames, color_doc)
        _write(ref_dir / "sheets.json", doc)
        return {"timeline_pages": len(doc["timeline"]["pages"]), "shot_pages": len(doc["shots"]["pages"]),
                "timecode_burned": doc["timeline"]["timecode_burned"]}
    records["sheets"] = _derived(ref_dir, "sheets", do_sheets, mode=mode)
    shutil.rmtree(work, ignore_errors=True)
    return {name: records[name] for name in DERIVED_STAGES if name in records}


# ---------------------------------------------------------------------------------------- coverage
def build_coverage(manifest: dict[str, Any], index: dict[str, Any] | None, meas: dict[str, Any] | None,
                   index_error: str | None, derived: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    if index is None:
        decode_status, expected, decoded = "partial", None, 0
        reasons.append(f"frame index unavailable: {index_error}")
    else:
        expected = index["frame_count"]
        decoded = meas["decoded_frames"] if meas else 0
        decode_status = "full"
        if index.get("nb_read_frames") not in (None, expected):
            decode_status = "partial"; reasons.append(f"ffprobe counted {index['nb_read_frames']} frames but indexed {expected}")
        if meas is None or decoded != expected:
            decode_status = "partial"; reasons.append(f"decoded {decoded} of {expected} indexed frames")
        if index.get("missing_pts"):
            reasons.append(f"{index['missing_pts']} frames without PTS")
        declared = index.get("nb_frames_declared")
        if declared and declared > expected:
            decode_status = "partial"; reasons.append(f"stream declares {declared} frames but only {expected} are present")
        vid = (manifest.get("probe") or {}).get("video") or {}
        declared_dur = vid.get("duration_s") or (manifest.get("probe") or {}).get("duration_s")
        last = index.get("last_pts_time")
        if declared_dur and last is not None and declared_dur - last > 0.5:
            decode_status = "partial"; reasons.append(f"declared duration {declared_dur:.2f}s but last frame at {last:.2f}s")
        if meas and meas.get("decode_error"):
            reasons.append(f"decoder: {meas['decode_error']}")
    measurement_status = "full" if (meas and meas["rows"] == decoded and decoded > 0) else "partial"
    if meas and meas["rows"] != decoded:
        reasons.append(f"measured {meas['rows']} of {decoded} decoded frames")
    stages = {}
    for name in DERIVED_STAGES:
        rec = (derived or {}).get(name)
        if rec is None:
            stages[name] = {"status": "not_run"}
        else:
            stages[name] = {"status": rec["status"], "elapsed_s": rec.get("elapsed_s"), **({"reason": rec["error"]} if rec.get("error") else {}),
                            **({"reason": rec["summary"].get("reason")} if rec.get("summary", {}).get("reason") else {})}
    return {
        "schema_version": "1.1.0", "asset_id": manifest["asset_id"],
        "decode": decode_status, "measurement": measurement_status, "model_exposure": "none",
        "expected_frames": expected, "decoded_frames": decoded, "measured_frames": meas["rows"] if meas else 0,
        "vfr": index["vfr"] if index else None, "frames_format": meas["format"] if meas else None,
        "stages": stages, "reasons": reasons, "pipeline_version": PIPELINE_VERSION, "iris_version": __version__,
        "generated_at": now_iso(),
    }


# --------------------------------------------------------------------------------------------- entry
def analyze(asset_id: str, mode: str = "economy", workspace: Path | None = None, force: bool = False,
            stages: list[str] | None = None) -> dict[str, Any]:
    if mode not in ("economy", "strict"):
        raise AnalyzeError("mode must be economy or strict", "usage")
    manifest = ingest.load_manifest(asset_id, workspace)
    store = Store(workspace)
    try:
        key = job_key({"sha256": manifest["sha256"], "pipeline": PIPELINE_VERSION, "measure": measure.METHOD_VERSION,
                       "width": ANALYSIS_WIDTH, "mode": mode})
        job, created = store.create_or_get_job(key, asset_id, "analyze", mode)
        ref_dir = store.workspace / "refs" / asset_id
        cov_path = ref_dir / "coverage.json"
        if force and not created:
            # keep index and per-frame measurement (versioned in the job key); recompute the derived stages
            # asked for (default all) plus the stages that consume their output
            targets = set(stages or DERIVED_STAGES)
            unknown = targets - set(DERIVED_STAGES)
            if unknown:
                raise AnalyzeError(f"unknown stages: {sorted(unknown)}; choose from {DERIVED_STAGES}", "usage")
            for name in list(targets):
                targets.update(DERIVED_DEPENDENTS[name])
            for name in targets:
                (ref_dir / f"{name}.done.json").unlink(missing_ok=True)
            cov_path.unlink(missing_ok=True)
            job = store.update_job(job["job_id"], state="measuring")
        elif not created and job["state"] in ("review_ready", "partial", "failed") and "coverage" in job["stages_done"] and cov_path.exists():
            cov = _read(cov_path)
            return {"job": job, "created": False, "coverage": cov, "stages": cov.get("stages")}
        try:
            with store.heavy_job_lock():
                return _run(store, job, manifest, ref_dir, mode)
        except BlockingIOError:
            raise AnalyzeError("another heavy job holds the lock", "locked")
    finally:
        store.close()


def _run(store: Store, job: dict[str, Any], manifest: dict[str, Any], ref_dir: Path, mode: str) -> dict[str, Any]:
    index: dict[str, Any] | None = None
    meas: dict[str, Any] | None = None
    derived: dict[str, dict[str, Any]] = {}
    index_error: str | None = None
    try:
        src = ingest.source_path(manifest)
    except ingest.IngestError as exc:
        store.update_job(job["job_id"], state="failed", error=str(exc))
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
        if meas["rows"] > 0:
            derived = run_derived_stages(src, ref_dir, manifest, index, mode)
            for name, rec in derived.items():
                if rec["status"] in ("ok", "skipped", "absent"):
                    job = store.update_job(job["job_id"], stage_done=name)

    coverage = build_coverage(manifest, index, meas, index_error, derived)
    _write(ref_dir / "coverage.json", coverage)
    final_state = "review_ready" if coverage["decode"] == "full" and coverage["measurement"] == "full" else "partial"
    job = store.update_job(job["job_id"], state=final_state, stage_done="coverage")
    return {"job": job, "created": True, "coverage": coverage,
            "index_summary": None if index is None else {k: index[k] for k in ("frame_count", "nb_read_frames", "vfr", "nominal_fps", "first_pts_time", "last_pts_time")},
            "measure_summary": meas, "stages": {k: {kk: vv for kk, vv in v.items() if kk != "trace"} for k, v in derived.items()}}
