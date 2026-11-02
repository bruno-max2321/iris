"""Child-process workers for native inference backends (PaddleOCR, faster-whisper).

Why a separate interpreter: PaddlePaddle and CTranslate2 each ship their own OpenMP runtime. In one
process they contend; on the VM, whisper went from 15 s to 700 s after PaddleOCR had run inference in
the same interpreter. Each backend therefore runs in its own interpreter with capped threads, writes
progress to a JSONL file the parent watches, and the parent enforces wall-clock budgets by killing the
child. A stalled frame costs one restart, not the stage.

Protocol: `python -m iris.worker <task>`; JSON payload on stdin; one JSON object per line appended to
`payload["progress"]`; final JSON result on stdout. Tasks: ocr, whisper, echo (tests)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, TextIO

DEFAULT_THREADS = int(os.environ.get("IRIS_WORKER_THREADS", "3"))


def child_env(threads: int) -> dict[str, str]:
    env = dict(os.environ)
    n = str(max(1, threads))
    env.update({
        "OMP_NUM_THREADS": n, "MKL_NUM_THREADS": n, "OPENBLAS_NUM_THREADS": n, "NUMEXPR_NUM_THREADS": n,
        "KMP_BLOCKTIME": "0", "OMP_WAIT_POLICY": "PASSIVE",
        "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false",
    })
    return env


# ----------------------------------------------------------------------------------------- parent side
def run_worker(task: str, payload: dict[str, Any], *, threads: int = DEFAULT_THREADS, first_budget_s: float,
               stall_budget_s: float, total_budget_s: float, workdir: Path | None = None) -> dict[str, Any]:
    """Run a worker task under supervision. Returns:
    {"exit": int|None, "killed": None|"stall"|"total", "result": dict|None, "events": [...], "stderr_tail": str,
     "elapsed_s": float, "progress_path": str}"""
    workdir = Path(workdir or tempfile.mkdtemp(prefix="iris-worker-"))
    workdir.mkdir(parents=True, exist_ok=True)
    progress = workdir / f"{task}_progress.jsonl"
    progress.write_text("")
    payload = dict(payload, progress=str(progress), threads=threads)
    err_path = workdir / f"{task}_stderr.log"
    t0 = time.time()
    with open(err_path, "w", encoding="utf-8") as err_fh:
        proc = subprocess.Popen([sys.executable, "-m", "iris.worker", task], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=err_fh, env=child_env(threads), text=True)
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(payload))
        proc.stdin.close()
        killed: str | None = None
        last_size, last_progress = 0, t0
        while True:
            rc = proc.poll()
            if rc is not None:
                break
            now = time.time()
            size = progress.stat().st_size if progress.exists() else 0
            if size != last_size:
                last_size, last_progress = size, now
            budget = first_budget_s if last_size == 0 else stall_budget_s
            if now - last_progress > budget:
                killed = "stall"
            elif now - t0 > total_budget_s:
                killed = "total"
            if killed:
                proc.kill()
                proc.wait(timeout=30)
                break
            time.sleep(0.25)
        out = proc.stdout.read() if proc.stdout else ""
    events: list[dict[str, Any]] = []
    for line in progress.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    result = None
    for line in reversed(out.strip().splitlines()):
        try:
            result = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    stderr_tail = err_path.read_text(encoding="utf-8", errors="ignore")[-1500:]
    return {"exit": proc.returncode, "killed": killed, "result": result, "events": events, "stderr_tail": stderr_tail,
            "elapsed_s": round(time.time() - t0, 3), "progress_path": str(progress)}


# ------------------------------------------------------------------------------------------ child side
def _emit(fh: TextIO, obj: dict[str, Any]) -> None:
    fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fh.flush()


def task_echo(payload: dict[str, Any], fh: TextIO) -> dict[str, Any]:
    for i in range(int(payload.get("n", 3))):
        time.sleep(float(payload.get("sleep", 0.05)))
        _emit(fh, {"event": "tick", "i": i})
    if payload.get("hang_after") is not None and int(payload["hang_after"]) >= 0:
        time.sleep(3600)
    return {"status": "ok", "n": int(payload.get("n", 3))}


def task_ocr(payload: dict[str, Any], fh: TextIO) -> dict[str, Any]:
    from paddleocr import PaddleOCR  # type: ignore

    threads = int(payload.get("threads", DEFAULT_THREADS))
    lang = payload.get("lang", "en")
    mkldnn = bool(payload.get("mkldnn", False))
    t0 = time.time()
    kwargs = dict(
        lang=lang, device="cpu", enable_mkldnn=mkldnn, cpu_threads=threads,
        text_det_limit_side_len=int(payload.get("long_side", 960)), text_det_limit_type="max",
        use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
    )
    try:
        ocr = PaddleOCR(text_detection_model_name="PP-OCRv5_mobile_det", text_recognition_model_name="PP-OCRv5_mobile_rec", **kwargs)
        models = "PP-OCRv5_mobile_det + PP-OCRv5_mobile_rec"
    except TypeError:
        ocr = PaddleOCR(lang=lang, enable_mkldnn=mkldnn, use_doc_orientation_classify=False,
                        use_doc_unwarping=False, use_textline_orientation=False)
        models = "paddleocr default"
    _emit(fh, {"event": "ready", "models": models, "init_s": round(time.time() - t0, 3), "mkldnn": mkldnn, "threads": threads})
    for img in payload["images"]:
        t1 = time.time()
        res = ocr.predict(img) if hasattr(ocr, "predict") else ocr.ocr(img)
        dets = []
        for page in res:
            polys = page.get("dt_polys") if isinstance(page, dict) else None
            if polys is not None:
                for poly, text, score in zip(polys, page.get("rec_texts", []), page.get("rec_scores", [])):
                    xs = [float(p[0]) for p in poly]; ys = [float(p[1]) for p in poly]
                    dets.append({"text": text, "conf": float(score), "box": [min(xs), min(ys), max(xs), max(ys)]})
            else:
                for item in page or []:
                    poly, (text, score) = item[0], item[1]
                    xs = [float(p[0]) for p in poly]; ys = [float(p[1]) for p in poly]
                    dets.append({"text": text, "conf": float(score), "box": [min(xs), min(ys), max(xs), max(ys)]})
        _emit(fh, {"event": "frame", "image": img, "dets": dets, "s": round(time.time() - t1, 3)})
    return {"status": "ok", "models": models}


def task_whisper(payload: dict[str, Any], fh: TextIO) -> dict[str, Any]:
    import numpy as np
    from faster_whisper import WhisperModel  # type: ignore

    threads = int(payload.get("threads", DEFAULT_THREADS))
    name = payload.get("model", "small")
    t0 = time.time()
    y = np.load(payload["pcm"]).astype(np.float32)
    model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=threads)
    _emit(fh, {"event": "ready", "model": name, "init_s": round(time.time() - t0, 3), "threads": threads})
    # temperature 0 only: the default fallback samples at higher temperatures when a segment looks poor, so
    # the same audio could give a different transcript on every run; not conditioning on the previous text
    # keeps one bad segment from dragging the rest into a repetition loop
    segments, info = model.transcribe(y, word_timestamps=True, vad_filter=True, temperature=0.0, condition_on_previous_text=False)
    words: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for seg in segments:
        text_parts.append(seg.text)
        for w in seg.words or []:
            words.append({"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "p": round(float(w.probability), 3)})
        _emit(fh, {"event": "segment", "end": round(float(seg.end), 3)})
    dur = max((w["end"] for w in words), default=0.0) - min((w["start"] for w in words), default=0.0)
    return {"status": "ok", "model": f"faster-whisper {name} int8", "language": info.language,
            "language_probability": round(float(info.language_probability), 3),
            "text": " ".join(t.strip() for t in text_parts), "words": words, "word_count": len(words),
            "words_per_minute": round(len(words) / dur * 60, 1) if dur > 0 else None,
            "elapsed_s": round(time.time() - t0, 3)}


TASKS: dict[str, Callable[[dict[str, Any], TextIO], dict[str, Any]]] = {"echo": task_echo, "ocr": task_ocr, "whisper": task_whisper}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in TASKS:
        print(json.dumps({"status": "failed", "reason": f"unknown task; expected one of {sorted(TASKS)}"}))
        return 2
    payload = json.load(sys.stdin)
    with open(payload["progress"], "a", encoding="utf-8") as fh:
        try:
            result = TASKS[argv[0]](payload, fh)
        except Exception as exc:  # noqa: BLE001 - the parent reads the reason from stdout and stderr
            import traceback

            traceback.print_exc()
            result = {"status": "failed", "reason": f"{type(exc).__name__}: {str(exc).splitlines()[0][:240] if str(exc) else ''}".rstrip(": ")}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
