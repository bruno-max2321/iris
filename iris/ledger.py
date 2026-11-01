"""Agent-call ledger and spend caps. One JSON line per model call in ledger/agent_calls.jsonl: request id,
exact model, tokens, cost, prompt and image hashes. Never the key, never the images themselves."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import paths

DEFAULT_PER_REFERENCE_USD = 1.5
DEFAULT_MONTHLY_CAP_USD = float(os.environ.get("IRIS_MONTHLY_CAP_USD", "100"))
WARN_SHARE = 0.8


def ledger_path(workspace: Path | None = None) -> Path:
    root = (workspace or paths.workspace_root()) / "ledger"
    root.mkdir(parents=True, exist_ok=True)
    return root / "agent_calls.jsonl"


def record(entry: dict[str, Any], workspace: Path | None = None) -> None:
    entry = dict(entry)
    entry.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with ledger_path(workspace).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def entries(workspace: Path | None = None) -> list[dict[str, Any]]:
    p = ledger_path(workspace)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _month(ts: str) -> str:
    return ts[:7]


def spent(workspace: Path | None = None, month: str | None = None, asset_id: str | None = None) -> float:
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    total = 0.0
    for e in entries(workspace):
        if _month(e.get("ts", "")) != month:
            continue
        if asset_id and e.get("asset_id") != asset_id:
            continue
        total += float(e.get("cost_usd") or 0.0)
    return round(total, 6)


def summary(workspace: Path | None = None, month: str | None = None) -> dict[str, Any]:
    month = month or datetime.now(timezone.utc).strftime("%Y-%m")
    rows = [e for e in entries(workspace) if _month(e.get("ts", "")) == month]
    by_asset: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}
    for e in rows:
        for key, bucket in ((e.get("asset_id") or "-", by_asset), (e.get("model") or "-", by_model)):
            b = bucket.setdefault(key, {"calls": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0})
            b["calls"] += 1
            b["cost_usd"] = round(b["cost_usd"] + float(e.get("cost_usd") or 0.0), 6)
            for k in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
                b[k] += int((e.get("usage") or {}).get(k) or 0)
    total = round(sum(float(e.get("cost_usd") or 0.0) for e in rows), 6)
    cap = DEFAULT_MONTHLY_CAP_USD
    return {"month": month, "calls": len(rows), "cost_usd": total, "monthly_cap_usd": cap,
            "share_of_cap": round(total / cap, 4) if cap else None, "warn": bool(cap and total >= WARN_SHARE * cap),
            "exhausted": bool(cap and total >= cap), "by_asset": by_asset, "by_model": by_model}


def check_budget(asset_id: str, max_usd: float, workspace: Path | None = None) -> tuple[bool, str | None]:
    """(ok, reason). The monthly cap is a local guard; the hard cap lives in the Anthropic console."""
    month_total = spent(workspace)
    if DEFAULT_MONTHLY_CAP_USD and month_total >= DEFAULT_MONTHLY_CAP_USD:
        return False, f"monthly cap reached: {month_total:.2f} of {DEFAULT_MONTHLY_CAP_USD:.2f} USD"
    ref_total = spent(workspace, asset_id=asset_id)
    if ref_total >= max_usd:
        return False, f"per-reference cap reached for {asset_id}: {ref_total:.3f} of {max_usd:.2f} USD"
    return True, None
