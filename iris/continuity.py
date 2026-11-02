"""Continuity metrics shared by `style build` (which derives rules) and `iris check` (which enforces them).

A rule names a metric from METRICS and a tolerance string. Each metric knows how to read its units
(shots, caption tracks, the audio track, the whole sequence) from one asset's stage outputs. When the
asset has nothing the metric needs (no audio stream, no text, region absent in every shot, stage
skipped), the extractor returns None and the rule is `not_applicable`: a rule never passes by absence."""

from __future__ import annotations

import re
from typing import Any, Callable

import numpy as np

from .regions import ciede2000

# bible region name -> region key in color.json
REGION_KEYS = {"background": "background", "subject": "subject", "skin": "skin", "graphics": "graphics", "frame": "whole_frame"}


class ToleranceError(ValueError):
    pass


_NUM = r"(-?\d+(?:\.\d+)?)"


def parse_tolerance(text: str) -> tuple:
    """'<= 6' | '>= -18' | 'within [a, b]' | 'within a-b' (non-negative) | 'in {x, y}' | '== x'."""
    s = (text or "").strip()
    m = re.fullmatch(rf"(<=|>=|<|>)\s*{_NUM}", s)
    if m:
        op = {"<=": "le", "<": "le", ">=": "ge", ">": "ge"}[m.group(1)]
        return (op, float(m.group(2)))
    m = re.fullmatch(rf"within\s*\[\s*{_NUM}\s*,\s*{_NUM}\s*\]", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if b < a:
            raise ToleranceError(f"empty interval: {text!r}")
        return ("within", a, b)
    m = re.fullmatch(r"within\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if b < a:
            raise ToleranceError(f"empty interval: {text!r}")
        return ("within", a, b)
    m = re.fullmatch(r"in\s*\{\s*([a-z0-9_.,\s]+)\}", s)
    if m:
        items = frozenset(x.strip() for x in m.group(1).split(",") if x.strip())
        if not items:
            raise ToleranceError(f"empty set: {text!r}")
        return ("in", items)
    m = re.fullmatch(r"==\s*([a-z0-9_.]+)", s)
    if m:
        return ("in", frozenset([m.group(1)]))
    raise ToleranceError(f"cannot parse tolerance {text!r}; use '<= x', '>= x', 'within [a, b]' or 'in {{a, b}}'")


def satisfies(value: Any, tol: tuple) -> bool:
    kind = tol[0]
    if kind == "in":
        return str(value) in tol[1]
    v = float(value)
    if kind == "le":
        return v <= tol[1] + 1e-9
    if kind == "ge":
        return v >= tol[1] - 1e-9
    return tol[1] - 1e-9 <= v <= tol[2] + 1e-9


# ------------------------------------------------------------------------------------------ units
def _fps(docs: dict[str, Any]) -> float:
    return float((docs.get("shots") or {}).get("fps_nominal") or 30.0)


def _shot_unit(s: dict[str, Any], value: Any) -> dict[str, Any]:
    mid = (s.get("keyframes") or {}).get("mid", s.get("frame_first"))
    return {"value": value, "shot_id": s["shot_id"], "frame": int(mid), "t": f"{float(s['t_in']):.2f}-{float(s['t_out']):.2f}"}


def caption_tracks(docs: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Caption-like OCR tracks, or None when the text stage did not run (absence of data, not of text)."""
    text = docs.get("text") or {}
    if text.get("status") not in (None, "ok") or "tracks" not in text:
        return None
    if (docs.get("coverage") or {}).get("stages", {}).get("text", {}).get("status") not in (None, "ok"):
        return None
    tracks = text.get("tracks") or []
    caps = [t for t in tracks if t.get("class") == "subtitle_candidate" or t.get("zone") in ("middle_band", "lower_third")]
    return caps or tracks


def _track_unit(t: dict[str, Any], value: Any, fps: float) -> dict[str, Any]:
    f0, f1 = int(t.get("frame_first_seen", 0)), int(t.get("frame_last_seen", 0))
    return {"value": value, "track_id": t.get("track_id"), "frame": f0, "t": f"{f0 / fps:.2f}-{(f1 + 1) / fps:.2f}"}


def style_lab(bible: dict[str, Any], region: str) -> np.ndarray | None:
    reg = ((bible.get("color") or {}).get("regions") or {}).get(region) or {}
    try:
        return np.array([reg["L"]["typical"], reg["a"]["typical"], reg["b"]["typical"]], dtype=float)
    except (KeyError, TypeError):
        return None


def _color_units(docs: dict[str, Any], region: str, fn: Callable[[dict[str, Any]], Any]) -> list[dict[str, Any]] | None:
    color = docs.get("color") or {}
    shots = {s["shot_id"]: s for s in (docs.get("shots") or {}).get("shots", [])}
    key = REGION_KEYS.get(region)
    if key is None or not color.get("shots"):
        return None
    out = []
    for c in color["shots"]:
        st = (c.get("regions") or {}).get(key)
        if c.get("status") != "ok" or not st or st.get("lab_mean") is None or c["shot_id"] not in shots:
            continue
        v = fn(st)
        if v is not None:
            out.append(_shot_unit(shots[c["shot_id"]], v))
    return out or None


def units_delta_e(docs, rule, bible):
    ref = style_lab(bible, rule.get("region") or "background")
    if ref is None:
        return None
    return _color_units(docs, rule.get("region") or "background", lambda st: round(ciede2000(np.array(st["lab_mean"], dtype=float), ref), 2))


def units_L(docs, rule, bible):
    return _color_units(docs, rule.get("region") or "frame", lambda st: round(float(st["lab_mean"][0]), 2))


def _light_units(docs, field, skip):
    color = docs.get("color") or {}
    shots = {s["shot_id"]: s for s in (docs.get("shots") or {}).get("shots", [])}
    out = []
    for c in color.get("shots") or []:
        v = (c.get("light") or {}).get(field)
        if c.get("status") == "ok" and v and v not in skip and c["shot_id"] in shots:
            out.append(_shot_unit(shots[c["shot_id"]], v))
    return out or None


def units_light_side(docs, rule, bible):
    return _light_units(docs, "side", {"key_side_unclear", "unclear"})


def units_light_key(docs, rule, bible):
    return _light_units(docs, "key", {"unclear"})


def units_shot_length(docs, rule, bible):
    shots = (docs.get("shots") or {}).get("shots") or []
    return [_shot_unit(s, round(float(s["duration_s"]), 3)) for s in shots] or None


def units_cut_rate(docs, rule, bible):
    m = (docs.get("shots") or {}).get("montage") or {}
    v = (m.get("cuts_per_s") or {}).get("overall")
    if v is None:
        return None
    return [{"value": round(float(v), 3), "frame": 0, "t": f"0.00-{float(m.get('duration_s') or 0):.2f}"}]


def units_caption_zone(docs, rule, bible):
    caps = caption_tracks(docs)
    if not caps:
        return None
    fps = _fps(docs)
    return [_track_unit(t, t.get("zone"), fps) for t in caps if t.get("zone")] or None


def units_caption_size(docs, rule, bible):
    caps = caption_tracks(docs)
    if not caps:
        return None
    fps = _fps(docs)
    return [_track_unit(t, float(t["rel_height"]), fps) for t in caps if t.get("rel_height") is not None] or None


def _audio(docs) -> dict[str, Any] | None:
    a = docs.get("audio") or {}
    return a if a.get("status") == "ok" else None


def units_lufs(docs, rule, bible):
    a = _audio(docs)
    v = ((a or {}).get("loudness") or {}).get("integrated_lufs")
    return None if v is None else [{"value": float(v), "frame": 0, "t": "0.00-end"}]


def units_true_peak(docs, rule, bible):
    a = _audio(docs)
    v = ((a or {}).get("loudness") or {}).get("true_peak_dbtp")
    return None if v is None else [{"value": float(v), "frame": 0, "t": "0.00-end"}]


METRICS: dict[str, dict[str, Any]] = {
    "color.delta_e2000_vs_style": {"scopes": {"every_shot"}, "kind": "number", "region": True, "units": units_delta_e},
    "color.L_mean": {"scopes": {"every_shot"}, "kind": "number", "region": True, "units": units_L},
    "light.side": {"scopes": {"every_shot"}, "kind": "set", "dimension": "light.side", "units": units_light_side},
    "light.key": {"scopes": {"every_shot"}, "kind": "set", "dimension": "light.key", "units": units_light_key},
    "rhythm.shot_length_s": {"scopes": {"every_shot"}, "kind": "number", "units": units_shot_length},
    "montage.cuts_per_s": {"scopes": {"sequence"}, "kind": "number", "units": units_cut_rate},
    "typography.zone": {"scopes": {"text_layers"}, "kind": "set", "units": units_caption_zone},
    "typography.size_rel_frame_h": {"scopes": {"text_layers"}, "kind": "number", "units": units_caption_size},
    "audio.integrated_lufs": {"scopes": {"audio"}, "kind": "number", "units": units_lufs},
    "audio.true_peak_dbtp": {"scopes": {"audio"}, "kind": "number", "units": units_true_peak},
}

ZONES = {"upper_third", "middle_band", "lower_third"}


def rule_problems(rule: dict[str, Any]) -> list[str]:
    """Static checks: known metric, scope, region, parseable tolerance of the right kind."""
    m = METRICS.get(rule.get("metric", ""))
    if m is None:
        return [f"{rule.get('rule_id')}: unknown metric {rule.get('metric')!r} (known: {', '.join(sorted(METRICS))})"]
    errs = []
    if rule.get("scope") not in m["scopes"]:
        errs.append(f"{rule['rule_id']}: metric {rule['metric']} needs scope {sorted(m['scopes'])}")
    if m.get("region") and rule.get("region") not in REGION_KEYS:
        errs.append(f"{rule['rule_id']}: metric {rule['metric']} needs a region in {sorted(REGION_KEYS)}")
    try:
        tol = parse_tolerance(rule.get("tolerance", ""))
    except ToleranceError as exc:
        return errs + [f"{rule['rule_id']}: {exc}"]
    if (tol[0] == "in") != (m["kind"] == "set"):
        errs.append(f"{rule['rule_id']}: metric {rule['metric']} takes a {'set' if m['kind'] == 'set' else 'numeric'} tolerance")
    return errs


def evaluate(rule: dict[str, Any], docs: dict[str, Any], bible: dict[str, Any], max_violations: int = 20) -> dict[str, Any]:
    out = {k: rule.get(k) for k in ("rule_id", "scope", "region", "metric", "tolerance", "severity")}
    out = {k: v for k, v in out.items() if v is not None}
    problems = rule_problems(rule)
    if problems:
        return {**out, "status": "not_applicable", "reason": "; ".join(problems), "units_evaluated": 0, "violations": []}
    tol = parse_tolerance(rule["tolerance"])
    units = METRICS[rule["metric"]]["units"](docs, rule, bible)
    if not units:
        return {**out, "status": "not_applicable", "reason": "the clip has none of the data this rule needs", "units_evaluated": 0, "violations": []}
    bad = [u for u in units if not satisfies(u["value"], tol)]
    status = rule.get("severity", "fail") if bad else "pass"
    return {**out, "status": status, "units_evaluated": len(units), "violations_total": len(bad), "violations": bad[:max_violations]}
