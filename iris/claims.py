"""Claims: generation (code + model), validation, listing and human review.

`validate` is idempotent: it rebuilds the evidence index and every claim from the current stage outputs
and judge answers, keeps claim ids stable through `claim_key`, preserves review decisions already
recorded, and rejects anything outside the contract (term not in the registry, evidence that does not
exist, wrong vocabulary version, schema violation). Review decisions are append-only events."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import evidence, interpret, paths, registry
from .store import Store

DECIDED = ("accepted", "corrected", "rejected")
STATUSES = ("pending", "needs_review", "accepted", "corrected", "rejected")


class ClaimsError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ref_dir(asset_id: str, workspace: Path | None) -> Path:
    return (workspace or paths.workspace_root()) / "refs" / asset_id


def _schema() -> dict[str, Any]:
    return json.loads((paths.SCHEMAS_DIR / "claim.schema.json").read_text(encoding="utf-8"))


def check_claim(claim: dict[str, Any], idx: dict[str, Any], validator: Any) -> list[str]:
    errs = [f"schema: {'/'.join(str(x) for x in e.path)}: {e.message[:140]}" for e in validator.iter_errors(claim)]
    if not registry.resolve(claim.get("term_id", "")):
        errs.append(f"term not in registry: {claim.get('term_id')}")
    if claim.get("vocabulary_version") != registry.vocabulary_version():
        errs.append(f"vocabulary version {claim.get('vocabulary_version')} != {registry.vocabulary_version()}")
    for e in claim.get("evidence_ids") or []:
        if e not in idx:
            errs.append(f"evidence id does not exist: {e}")
    if claim.get("corrected_term_id") and not registry.resolve(claim["corrected_term_id"]):
        errs.append(f"corrected term not in registry: {claim['corrected_term_id']}")
    for k in ("time_span", "frame_range"):
        if any(isinstance(v, bool) for v in (claim.get(k) or {}).values()):
            errs.append(f"{k} holds a boolean")
    if claim.get("source") == "model" and claim.get("claim_kind") != "interpreted":
        errs.append("model-sourced claims must be 'interpreted'")
    return errs


def validate_asset(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    import jsonschema

    ref_dir = _ref_dir(asset_id, workspace)
    docs = evidence.load_docs(ref_dir)
    if not docs.get("shots"):
        raise ClaimsError("analyze has not produced shots.json for this asset")
    idx = evidence.build_index(docs)
    evidence.write_index(ref_dir, idx)
    generated = evidence.code_claims(asset_id, docs, idx)
    packet_path = ref_dir / "interpret" / "packet.json"
    answers = interpret.load_answers(ref_dir)
    abstentions: list[dict[str, Any]] = []
    agree = None
    if packet_path.exists() and answers:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        model_claims, abstentions = interpret.fuse(asset_id, packet, answers, docs["shots"], idx)
        generated.extend(model_claims)
        agree = interpret.agreement(packet, answers)

    validator = jsonschema.Draft202012Validator(_schema())
    store = Store(workspace)
    try:
        existing = {c["claim_key"]: c for c in store.list_claims(asset_id)}
        new_keys = [c["claim_key"] for c in generated if c["claim_key"] not in existing]
        new_ids = store.next_claim_ids(len(new_keys)) if new_keys else []
        id_for = dict(zip(new_keys, new_ids))
        errors: dict[str, list[str]] = {}
        final: list[dict[str, Any]] = []
        for c in generated:
            prev = existing.get(c["claim_key"])
            c["claim_id"] = prev["claim_id"] if prev else id_for[c["claim_key"]]
            c["created_at"] = prev["created_at"] if prev else _now()
            c["updated_at"] = _now()
            if prev and prev.get("review_status") in DECIDED:
                c["review_status"] = prev["review_status"]
                c["corrected_term_id"] = prev.get("corrected_term_id")
            errs = check_claim(c, idx, validator)
            if errs:
                errors[c["claim_id"]] = errs
                continue
            store.upsert_claim(c)
            final.append(c)
        # claims whose source disappeared (stage re-run) stay in the store but are flagged as stale in the report
        stale = sorted(set(existing) - {c["claim_key"] for c in generated})
    finally:
        store.close()
    final.sort(key=lambda c: c["claim_id"])
    (ref_dir / "claims.json").write_text(json.dumps({"schema_version": "1.0.0", "asset_id": asset_id, "count": len(final), "claims": final}, indent=1, ensure_ascii=False), encoding="utf-8")
    by_kind: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for c in final:
        by_kind[c["claim_kind"]] = by_kind.get(c["claim_kind"], 0) + 1
        by_status[c["review_status"]] = by_status.get(c["review_status"], 0) + 1
        by_source[c["source"]] = by_source.get(c["source"], 0) + 1
    report = {
        "schema_version": "1.0.0", "asset_id": asset_id, "generated_at": _now(), "ok": not errors,
        "claims": len(final), "rejected_by_validator": len(errors), "errors": errors, "stale_claim_keys": stale,
        "evidence_count": len(idx), "by_kind": by_kind, "by_status": by_status, "by_source": by_source,
        "judges_present": sorted(answers), "abstentions": len(abstentions), "agreement": agree,
        "review_queue": [c["claim_id"] for c in final if c["review_status"] in ("needs_review",)] + [c["claim_id"] for c in final if c["review_status"] == "pending" and c["source"] == "model"],
    }
    (ref_dir / "validate.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return report


def list_claims(asset_id: str, kind: str | None = None, status: str | None = None, source: str | None = None, workspace: Path | None = None) -> list[dict[str, Any]]:
    store = Store(workspace)
    try:
        rows = store.list_claims(asset_id)
    finally:
        store.close()
    return [c for c in rows if (not kind or c["claim_kind"] == kind) and (not status or c["review_status"] == status) and (not source or c["source"] == source)]


# ------------------------------------------------------------------------------------------- review
_RANGE = re.compile(r"^c_(\d{6})(?:\s*-\s*c_(\d{6}))?$")


def expand_ids(spec: str) -> list[str]:
    ids: list[str] = []
    for part in [p.strip() for p in spec.replace(";", ",").split(",") if p.strip()]:
        m = _RANGE.match(part)
        if not m:
            raise ClaimsError(f"bad claim id or range: {part!r}", "usage")
        a = int(m.group(1)); b = int(m.group(2) or m.group(1))
        if b < a:
            raise ClaimsError(f"descending range: {part!r}", "usage")
        ids.extend(f"c_{i:06d}" for i in range(a, b + 1))
    return ids


_LINE = re.compile(r"^\s*(accept|reject|correct)\s+(c_\d{6}(?:\s*-\s*c_\d{6})?(?:\s*,\s*c_\d{6}(?:\s*-\s*c_\d{6})?)*)(?:\s+to\s+(\S+))?\s*(?::\s*(.*))?$", re.IGNORECASE)


def parse_batch_line(line: str) -> list[dict[str, Any]]:
    """`accept c_000012-c_000040` | `reject c_000041: reason` | `correct c_000044 to camera.movement=dolly_in: reason`."""
    line = line.strip()
    if not line or line.startswith("#"):
        return []
    m = _LINE.match(line)
    if not m:
        raise ClaimsError(f"cannot parse review line: {line!r}", "usage")
    verb, spec, value, reason = m.group(1).lower(), m.group(2), m.group(3), (m.group(4) or "").strip() or None
    status = {"accept": "accepted", "reject": "rejected", "correct": "corrected"}[verb]
    if status == "corrected" and not value:
        raise ClaimsError(f"'correct' needs 'to <dimension=term>': {line!r}", "usage")
    return [{"claim_id": cid, "status": status, "value": value, "reason": reason} for cid in expand_ids(spec)]


def apply_decisions(decisions: list[dict[str, Any]], author: str, workspace: Path | None = None) -> dict[str, Any]:
    store = Store(workspace)
    recorded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    touched_assets: set[str] = set()
    try:
        for d in decisions:
            claim = store.get_claim(d["claim_id"])
            if claim is None:
                errors.append({**d, "error": "unknown claim id"})
                continue
            if d["status"] not in DECIDED:
                errors.append({**d, "error": f"status must be one of {DECIDED}"})
                continue
            value = d.get("value")
            if d["status"] == "corrected":
                ref = registry.resolve(value or "")
                if ref is None:
                    errors.append({**d, "error": f"corrected value not in registry: {value}"})
                    continue
                if ref.dimension != claim["dimension"]:
                    errors.append({**d, "error": f"corrected term belongs to {ref.dimension}, claim is {claim['dimension']}"})
                    continue
                value = f"{ref.dimension}={ref.term}"
            if d["status"] == "rejected" and not d.get("reason"):
                errors.append({**d, "error": "a rejection needs a reason"})
                continue
            ev = store.add_review_event(claim["claim_id"], d["status"], author, value, d.get("reason"))
            claim["review_status"] = d["status"]
            claim["corrected_term_id"] = value if d["status"] == "corrected" else None
            claim["updated_at"] = ev["ts"]
            store.upsert_claim(claim)
            touched_assets.add(claim["asset_id"])
            recorded.append({"claim_id": claim["claim_id"], "term_id": claim["term_id"], "status": d["status"], "value": value, "reason": d.get("reason"), "ts": ev["ts"], "author": author})
        # keep claims.json in sync for every touched asset
        for asset_id in touched_assets:
            rows = store.list_claims(asset_id)
            (_ref_dir(asset_id, workspace) / "claims.json").write_text(json.dumps({"schema_version": "1.0.0", "asset_id": asset_id, "count": len(rows), "claims": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    finally:
        store.close()
    return {"ok": not errors, "recorded": recorded, "errors": errors, "author": author}
