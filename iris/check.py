"""Stage M: `iris check <clip> --against <style_id>`.

The clip is ingested and analysed like any reference (economy mode, every measurement stage, no model
call), then every continuity rule and every `never` term of the Style Bible is evaluated:

- `pass` when the clip has the data the rule needs and every unit satisfies the tolerance;
- `fail` / `warn` (the rule's severity) with the frame and time of each violating unit;
- `not_applicable` when the clip has none of the data the rule needs (no audio, no text, region absent,
  stage skipped). A rule never passes by absence.

`never` terms are evaluated against the code's own estimates for the clip (camera movement, light key /
side / quality, montage pacing, caption cadence). A term whose dimension the code cannot estimate is
`not_applicable`; it needs a judge, and `check` never calls one."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import analyze, continuity, evidence, ingest, paths, registry, style

METHOD_VERSION = "check@0.1.0"
NEVER_BLOCKS = ["camera", "light", "color", "composition", "environment", "typography", "animation", "montage", "sound"]


class CheckError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def evaluate_never(bible: dict[str, Any], asset_id: str, docs: dict[str, Any]) -> list[dict[str, Any]]:
    idx = evidence.build_index(docs)
    labels: dict[str, list[dict[str, Any]]] = {}
    for c in evidence.code_claims(asset_id, docs, idx):
        labels.setdefault(c["dimension"], []).append(c)
    out = []
    items = [(b, t) for b in NEVER_BLOCKS for t in (bible.get(b) or {}).get("never") or []] + [("never_global", t) for t in bible.get("never_global") or []]
    for block, term in items:
        ref = registry.resolve(term)
        row: dict[str, Any] = {"block": block, "term": term}
        if ref is None:
            out.append({**row, "status": "not_applicable", "reason": "term not in the vocabulary"})
            continue
        got = labels.get(ref.dimension)
        if not got:
            out.append({**row, "status": "not_applicable", "reason": f"the code does not estimate {ref.dimension} on this clip; a judge is needed"})
            continue
        hits = [c for c in got if c["term_id"] == f"{ref.dimension}={ref.term}"]
        viol = [{"unit": c.get("unit_id") or c.get("temporal_unit"), "frame": c["frame_range"]["first"],
                 "t": f"{c['time_span']['start_seconds']:.2f}-{c['time_span']['end_seconds']:.2f}", "claim_kind": c["claim_kind"]} for c in hits]
        out.append({**row, "status": "fail" if hits else "pass", "units_evaluated": len(got), "violations": viol[:20]})
    return out


def overall(results: list[dict[str, Any]]) -> str:
    states = {r["status"] for r in results}
    if "fail" in states:
        return "fail"
    if "warn" in states:
        return "warn"
    if "pass" in states:
        return "pass"
    return "not_applicable"


def check(clip: str, style_id: str, rights: str = "own", mode: str = "economy", workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or paths.workspace_root()
    bible = style.load_bible(style_id, ws)
    lint = style.lint(style_id, ws)
    if not lint["ok"]:
        raise CheckError(f"Style Bible {style_id} does not lint: " + "; ".join(lint["issues"][:5]))
    try:
        rec = ingest.ingest(clip, rights, workspace=ws)
    except ingest.IngestError as exc:
        raise CheckError(f"cannot ingest the clip: {exc}", exc.code) from exc
    asset_id = rec["asset_id"]
    try:
        analyze.analyze(asset_id, mode=mode, workspace=ws)
    except analyze.AnalyzeError as exc:
        raise CheckError(f"analyze failed on the clip: {exc}", exc.code) from exc
    ref_dir = ws / "refs" / asset_id
    docs = evidence.load_docs(ref_dir)
    if not docs.get("shots"):
        raise CheckError("analyze produced no shots for the clip", "partial")
    rules = [continuity.evaluate(r, docs, bible) for r in bible.get("continuity_rules") or []]
    never = evaluate_never(bible, asset_id, docs)
    status = overall(rules + never)
    check_id = "chk_" + hashlib.sha256(f"{asset_id}|{lint['sha256']}".encode()).hexdigest()[:12]
    cov = docs.get("coverage") or {}
    report = {
        "schema_version": "1.0.0", "method_version": METHOD_VERSION, "check_id": check_id, "generated_at": _now(),
        "clip": {"asset_id": asset_id, "source": clip, "sha256": (rec.get("manifest") or {}).get("sha256"), "duration_s": ((docs["shots"].get("montage") or {}).get("duration_s"))},
        "style": {"style_id": style_id, "status": bible["status"], "sha256": lint["sha256"]},
        "status": status,
        "counts": {s: sum(1 for r in rules + never if r["status"] == s) for s in ("pass", "warn", "fail", "not_applicable")},
        "coverage": {"decode": cov.get("decode"), "measurement": cov.get("measurement"),
                     "stages": {k: v.get("status") for k, v in (cov.get("stages") or {}).items()}},
        "rules": rules, "never": never,
    }
    out = ws / "checks" / check_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "continuity_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    report["report_path"] = str(out / "continuity_report.json")
    return report
