"""Second judge: Claude through the Anthropic API.

One request per packet window: a cached system prompt (role, rules, lexicon cards of the requested
dimensions), the window's keyframes as images, the per-shot numeric summaries as text, and a JSON
schema enforced through structured outputs so the answer is always parseable. The adapter returns the
parsed answer plus usage, cost and request id; it never raises on model content, only on transport.

Model: the plan fixes `claude-sonnet-5-5` for this role (cheaper second judge; agreement with the Grok
judge is measured before anyone is trusted). Sampling parameters are not sent: this model rejects
non-default temperature. Refusal fallbacks are deliberately off: a silent model swap would corrupt the
judge-agreement statistics, so a refusal is reported as `needs_input` instead."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 8000
EFFORT = os.environ.get("IRIS_ANTHROPIC_EFFORT", "medium")

# USD per million tokens (Anthropic first-party rates; verify against the pricing page before a budget decision)
PRICES = {
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0, "cache_read": 0.20, "cache_write": 2.50},
    "claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.20, "cache_write": 5.00},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
}


class AdapterError(RuntimeError):
    def __init__(self, message: str, code: str = "provider", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def load_api_key(workspace: Path) -> str:
    """secrets/anthropic.key (mode 600) or ANTHROPIC_API_KEY. The value is never logged or echoed."""
    p = workspace / "secrets" / "anthropic.key"
    if p.exists():
        mode = stat.S_IMODE(p.stat().st_mode)
        if mode & 0o077:
            raise AdapterError(f"{p} must be mode 600 (is {oct(mode)})", code="validation")
        key = p.read_text(encoding="utf-8").strip()
        if key:
            return key
    env = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env:
        return env
    raise AdapterError("no API key: create secrets/anthropic.key (mode 600) or set ANTHROPIC_API_KEY", code="validation")


def cost_usd(model: str, usage: dict[str, int]) -> float:
    p = PRICES.get(model) or PRICES.get(model.rsplit("-", 1)[0]) or PRICES[DEFAULT_MODEL]
    return round(
        usage.get("input_tokens", 0) * p["input"] / 1e6
        + usage.get("output_tokens", 0) * p["output"] / 1e6
        + usage.get("cache_read_input_tokens", 0) * p["cache_read"] / 1e6
        + usage.get("cache_creation_input_tokens", 0) * p["cache_write"] / 1e6, 6)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _image_block(path: Path) -> dict[str, Any]:
    data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}


def build_system(lexicon: dict[str, Any], rules: str) -> list[dict[str, Any]]:
    """Two cached blocks: stable rules first, then the lexicon (both frozen per vocabulary version)."""
    return [
        {"type": "text", "text": rules, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "LEXICON (closed vocabulary; use only these term ids or 'unclear'):\n" + json.dumps(lexicon, ensure_ascii=False, sort_keys=True),
         "cache_control": {"type": "ephemeral"}},
    ]


def build_user_content(window: dict[str, Any], image_paths: dict[str, Path], text_summary: str) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for img in window.get("images", []):
        p = image_paths.get(img["evidence_id"])
        if p and p.exists():
            content.append({"type": "text", "text": f"[image evidence_id={img['evidence_id']}]"})
            content.append(_image_block(p))
    content.append({"type": "text", "text": text_summary})
    return content


def judge_window(client: Any, model: str, system: list[dict[str, Any]], user_content: list[dict[str, Any]],
                 schema: dict[str, Any], repair_errors: list[str] | None = None, previous_json: str | None = None) -> dict[str, Any]:
    """One structured-output call. Returns {"json": dict|None, "text": str, "usage": {...}, "request_id": str,
    "model": str, "stop_reason": str, "error": str|None}."""
    import anthropic

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]
    if repair_errors and previous_json is not None:
        messages.append({"role": "assistant", "content": [{"type": "text", "text": previous_json}]})
        messages.append({"role": "user", "content": [{"type": "text", "text": "Your previous answer failed validation:\n- " + "\n- ".join(repair_errors)
                                                      + "\nReturn a corrected answer. Only term ids from the lexicon or 'unclear'; only evidence ids listed in the packet."}]})
    try:
        resp = client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=system, messages=messages,
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": schema}},
        )
    except anthropic.RateLimitError as exc:
        raise AdapterError(f"rate limited: {exc.message}", retryable=True) from exc
    except anthropic.APIStatusError as exc:
        raise AdapterError(f"api error {exc.status_code}: {exc.message}", retryable=exc.status_code >= 500) from exc
    except anthropic.APIConnectionError as exc:
        raise AdapterError(f"connection error: {exc}", retryable=True) from exc
    usage = {k: int(getattr(resp.usage, k, 0) or 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
    out = {"json": None, "text": "", "usage": usage, "request_id": getattr(resp, "_request_id", None), "model": resp.model,
           "stop_reason": resp.stop_reason, "error": None}
    if resp.stop_reason == "refusal":
        details = getattr(resp, "stop_details", None)
        out["error"] = f"refusal ({getattr(details, 'category', None)}): {getattr(details, 'explanation', '')}"
        return out
    text = next((b.text for b in resp.content if b.type == "text"), "")
    out["text"] = text
    if resp.stop_reason == "max_tokens":
        out["error"] = "max_tokens reached before the answer was complete"
        return out
    try:
        out["json"] = json.loads(text)
    except json.JSONDecodeError as exc:
        out["error"] = f"answer is not JSON: {exc}"
    return out


def make_client(api_key: str) -> Any:
    import anthropic

    return anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=180.0)
