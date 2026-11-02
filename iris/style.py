"""Stage L: Style Bible build, lint, approve.

`build` aggregates N analysed references into styles/<style_id>/style_bible.json (+ .md, .sha256,
build_report.json):

- measured fields come straight from the stage outputs (code measurements are accepted as a block);
- estimated and interpreted labels come only from claims a human `accepted` or `corrected`, and a term
  is carried only when it appears in at least 2 of 3 references (all of them when fewer than 3);
- prose (identity, concept, environment settings, asset families, voice and CTA treatment), human
  terms, prohibitions and extra rules come from styles/<style_id>/brief.json; those blocks stay
  `pending` until the brief names `reviewed_by`;
- with fewer than 3 references every range is widened by the declared DEFAULT_TOLERANCES and the
  block is `provisional`; the bible is always built as `draft` (`style approve` promotes it);
- continuity rules are derived from the tightest measured ranges, plus the brief's rules;
- a field with no evidence is left out and named in the block's `meta.missing`; nothing is invented.

`lint` re-validates a stored bible: schema, term references against the vocabulary, distribution keys,
continuity rule metrics and tolerances, exemplars pointing at existing shots, token budget, Markdown
round trip and the stored hash."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__, continuity, evidence, paths, registry
from .store import Store

METHOD_VERSION = "style@0.1.0"
SCHEMA_VERSION = "1.1.0"
TOKEN_LIMIT = 3500
CHARS_PER_TOKEN = 3.2
TOKENIZER = "approx: compact JSON characters / 3.2 (conservative for English JSON)"
HOOK_S = 3.0
MEMBERSHIP_SHARE = 0.30
MASTER_MIN_COVERAGE = 0.20      # a region must cover this share of the frame (median) to anchor the colour rule
DELTA_E_FLOOR = 4.0             # colour rule tolerance never tighter than this (dE00)
DELTA_E_FLOOR_PROVISIONAL = 6.0 # with < 3 references the observed spread says little about the style
DELTA_E_CEILING = 10.0          # and never looser than this: a shift above it is a different grade
DECIDED = ("accepted", "corrected")

DEFAULT_TOLERANCES = {
    "duration_rel": 0.25, "cut_rate_rel": 0.30, "cut_rate_abs": 0.10, "shot_length_rel": 0.30, "count_abs": 1.0,
    "lufs_abs": 1.5, "true_peak_abs": 1.0, "L_abs": 6.0, "ab_abs": 4.0, "delta_e_abs": 2.0, "contrast_rel": 0.20,
    "type_size_rel": 0.15, "wpm_rel": 0.15, "cues_rel": 0.25, "words_abs": 1.0, "hold_rel": 0.25, "lead_ms_abs": 150.0,
    "share_abs": 0.10, "time_abs_s": 0.5,
}

# fields required by schema 1.0.0 that 1.1.0 lets a build omit; a missing one is listed in meta.missing
REQUIRED_V10 = {
    "identity": ["one_line", "iris_operations", "signature_techniques", "tone_words"],
    "concept": ["visual_concept", "metaphor_language", "subject_treatment", "viewer_promise"],
    "rhythm": ["duration_s", "hook", "cut_rate_per_s", "shot_length_s", "speech_wpm", "silence", "music_relation", "image_reuse"],
    "camera": ["movement", "shot_size", "angle", "support"],
    "light": ["key", "direction", "edge", "contrast_ratio", "scheme"],
    "color": ["grade_family", "regions", "delta_e_between_shots"],
    "composition": ["techniques", "subject_placement", "negative_space"],
    "environment": ["settings", "surfaces", "atmosphere"],
    "assets": ["families"],
    "typography": ["family_class", "weight", "case", "size_rel_frame_h", "placement", "lines", "entrance", "caption_cadence"],
    "animation": ["easing", "entrance_ms", "hold_ms", "exit_ms"],
    "montage": ["transitions", "editorial_transforms"],
    "sound": ["role", "loudness_lufs"],
    "narrative": ["structure", "hook_type", "text_role"],
}
VISUAL_NEVER = ["camera", "light", "color", "composition", "environment", "typography", "animation", "montage"]
BLOCKS = list(REQUIRED_V10)

# distribution field -> vocabulary dimension its keys belong to
DIST_DIMS = {
    ("camera", "movement"): "camera.movement", ("light", "direction"): "light.direction", ("composition", "techniques"): "composition",
    ("typography", "emphasis"): "typography.emphasis", ("montage", "transitions"): "montage.transition",
    ("narrative", "beat_share_of_runtime"): "narrative.function", ("sound", "role"): "sound.role",
}
TRANSITION_TERMS = {"cut": "hard_cut", "fade_in": "fade", "fade_out": "fade", "dissolve_candidate": "cross_dissolve"}
ZONE_TO_PLACEMENT = {"upper_third": "upper_third", "middle_band": "center", "lower_third": "lower_third"}
SAT_CLASSES = [(0.15, "low"), (0.30, "medium"), (0.45, "medium_high")]


class StyleError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ws(workspace: Path | None) -> Path:
    return workspace or paths.workspace_root()


def style_dir(style_id: str, workspace: Path | None = None) -> Path:
    return _ws(workspace) / "styles" / style_id


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _r(x: float, nd: int = 3) -> float:
    return float(round(float(x), nd))


# ------------------------------------------------------------------------------------- statistics
def quantiles(values: list[float], nd: int = 3, unit: str | None = None, widen: float = 0.0) -> dict[str, Any] | None:
    v = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not v:
        return None
    a = np.array(v)
    q = {"min": _r(a.min() - widen, nd), "p25": _r(np.percentile(a, 25), nd), "p50": _r(np.percentile(a, 50), nd),
         "p75": _r(np.percentile(a, 75), nd), "max": _r(a.max() + widen, nd)}
    if unit:
        q["unit"] = unit
    return q


def value_range(values: list[float], *, widen: bool, rel: float = 0.0, abs_: float = 0.0, nd: int = 3, unit: str | None = None,
                lo: float | None = None, hi: float | None = None, spread: tuple[float, float] | None = None) -> dict[str, Any] | None:
    """min/max/typical over the values (or the given percentile spread); widened by max(abs_, rel*|typical|) when `widen`."""
    v = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    if not v:
        return None
    a = np.array(v)
    typ = float(np.median(a))
    mn, mx = (float(np.percentile(a, spread[0])), float(np.percentile(a, spread[1]))) if spread else (float(a.min()), float(a.max()))
    if widen:
        d = max(abs_, rel * abs(typ))
        mn, mx = mn - d, mx + d
    if lo is not None:
        mn = max(lo, mn)
    if hi is not None:
        mx = min(hi, mx)
    out = {"min": _r(mn, nd), "max": _r(mx, nd), "typical": _r(typ, nd)}
    if unit:
        out["unit"] = unit
    return out


def saturation_class(sat: float) -> str:
    for limit, name in SAT_CLASSES:
        if sat < limit:
            return name
    return "high"


# ------------------------------------------------------------------------------------- references
def _effective_term(c: dict[str, Any]) -> str:
    return c["corrected_term_id"] if c.get("review_status") == "corrected" and c.get("corrected_term_id") else c["term_id"]


def load_reference(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    ref_dir = _ws(workspace) / "refs" / asset_id
    docs = evidence.load_docs(ref_dir)
    if not docs.get("shots") or not docs.get("coverage"):
        raise StyleError(f"{asset_id}: analyze has not completed (shots.json / coverage.json missing)")
    store = Store(workspace)
    try:
        claims = store.list_claims(asset_id)
    finally:
        store.close()
    decided = []
    for c in claims:
        if c.get("review_status") in DECIDED:
            ref = registry.resolve(_effective_term(c))
            if ref is not None:
                decided.append({**c, "eff_dimension": ref.dimension, "eff_term": ref.term})
    h = hashlib.sha256()
    for name in ("shots", "color", "text", "audio", "motion", "events", "coverage"):
        p = ref_dir / f"{name}.json"
        if p.exists():
            h.update(name.encode() + b"\0" + p.read_bytes())
    h.update(_canon(sorted([c["claim_id"], c["review_status"], _effective_term(c)] for c in decided)))
    return {"asset_id": asset_id, "dir": ref_dir, "docs": docs, "decided": decided, "claim_ids": {c["claim_id"] for c in claims},
            "inputs_sha256": h.hexdigest(), "fps": float(docs["shots"].get("fps_nominal") or 30.0)}


def _shots(rd) -> list[dict[str, Any]]:
    return rd["docs"]["shots"].get("shots", [])


def _montage(rd) -> dict[str, Any]:
    return rd["docs"]["shots"].get("montage") or {}


def _audio(rd) -> dict[str, Any] | None:
    a = rd["docs"].get("audio") or {}
    return a if a.get("status") == "ok" else None


def _caps(rd) -> list[dict[str, Any]] | None:
    return continuity.caption_tracks(rd["docs"])


def _blocks(rd) -> list[dict[str, Any]] | None:
    return continuity.caption_blocks(rd["docs"])


def _cap_duration_s(t, fps) -> float:
    return (int(t["frame_last_seen"]) - int(t["frame_first_seen"]) + 1) / fps


def _norm_word(w: str) -> str:
    return "".join(ch for ch in w.lower() if ch.isalnum())


def caption_leads_ms(rd) -> list[float]:
    """Caption onset minus the matching spoken word onset (negative = caption leads), for caption tracks
    whose first word is found in the transcript within 2 s."""
    a, caps = _audio(rd), _caps(rd)
    words = ((a or {}).get("transcript") or {}).get("words") or []
    if not words or not caps:
        return []
    spoken = [(_norm_word(w.get("w", "")), float(w["start"])) for w in words if w.get("start") is not None]
    out = []
    for t in caps:
        first = next((_norm_word(x) for x in (t.get("text") or "").split() if _norm_word(x)), "")
        if len(first) < 2:
            continue
        tc = int(t["frame_first_seen"]) / rd["fps"]
        cands = [ts for w, ts in spoken if w == first and abs(ts - tc) <= 2.0]
        if cands:
            ts = min(cands, key=lambda x: abs(x - tc))
            out.append((tc - ts) * 1000.0)
    return out


def ref_facts(rd) -> dict[str, float]:
    """Reference-level scalars used for ranges and for the membership warning."""
    m = _montage(rd)
    cps = m.get("cuts_per_s") or {}
    f: dict[str, float] = {}

    def put(k, v):
        if v is not None and math.isfinite(float(v)):
            f[k] = float(v)

    put("duration_s", m.get("duration_s"))
    for k in ("overall", "hook", "body", "close"):
        put(f"cuts_per_s.{k}", cps.get(k))
    put("cuts_in_hook", sum(1 for t in rd["docs"]["shots"].get("cut_times_s", []) if t < HOOK_S))
    put("shot_length_p50", (m.get("shot_length_s") or {}).get("p50"))
    put("unique_pictures", m.get("unique_pictures"))
    put("reuse_factor", m.get("reuse_factor"))
    a = _audio(rd)
    if a:
        loud = a.get("loudness") or {}
        put("loudness_lufs", loud.get("integrated_lufs"))
        put("true_peak_dbtp", loud.get("true_peak_dbtp"))
        put("share_cuts_on_onset", a.get("share_of_cuts_on_onset"))
        put("max_silence_gap_s", max([s["duration_s"] for s in a.get("silences") or []], default=0.0))
        tr = a.get("transcript") or {}
        if tr.get("status") == "ok":
            put("speech_wpm", tr.get("words_per_minute"))
    caps = _caps(rd)
    if caps:
        put("first_text_at_s", min(int(t["frame_first_seen"]) for t in caps) / rd["fps"])
        put("caption_size_p50", float(np.median([t["rel_height"] for t in caps])))
        blocks = _blocks(rd) or []
        if m.get("duration_s") and blocks:
            put("cues_per_10s", len(blocks) / float(m["duration_s"]) * 10.0)
        if blocks:
            put("words_per_cue_p50", float(np.median([b["words"] for b in blocks])))
    for region in ("background", "whole_frame"):
        vals = [c["regions"][region]["lab_mean"][0] for c in (rd["docs"].get("color") or {}).get("shots", [])
                if c.get("status") == "ok" and (c.get("regions") or {}).get(region)]
        if vals:
            put(f"{region}_L_p50", float(np.median(vals)))
    cr = [c["light"]["contrast_ratio_p95_p5"] for c in (rd["docs"].get("color") or {}).get("shots", [])
          if c.get("status") == "ok" and (c.get("light") or {}).get("contrast_ratio_p95_p5") is not None]
    if cr:
        put("contrast_p50", float(np.median(cr)))
    return f


FACT_TOL = {
    "duration_s": ("rel", "duration_rel"), "cuts_per_s.overall": ("cut", None), "cuts_per_s.hook": ("cut", None), "cuts_per_s.body": ("cut", None),
    "cuts_per_s.close": ("cut", None), "cuts_in_hook": ("abs", "count_abs"), "shot_length_p50": ("rel", "shot_length_rel"),
    "unique_pictures": ("abs", "count_abs"), "reuse_factor": ("rel", "cut_rate_rel"), "loudness_lufs": ("abs", "lufs_abs"),
    "true_peak_dbtp": ("abs", "true_peak_abs"), "share_cuts_on_onset": ("abs", "share_abs"), "max_silence_gap_s": ("abs", "time_abs_s"),
    "speech_wpm": ("rel", "wpm_rel"), "first_text_at_s": ("abs", "time_abs_s"), "caption_size_p50": ("rel", "type_size_rel"),
    "cues_per_10s": ("rel", "cues_rel"), "words_per_cue_p50": ("abs", "words_abs"), "background_L_p50": ("abs", "L_abs"),
    "whole_frame_L_p50": ("abs", "L_abs"), "contrast_p50": ("rel", "contrast_rel"),
}


def _fact_range(key: str, values: list[float], widen: bool) -> dict[str, Any] | None:
    kind, tk = FACT_TOL.get(key, ("abs", "share_abs"))
    if kind == "cut":
        typ = float(np.median(values)) if values else 0.0
        return value_range(values, widen=widen, abs_=max(DEFAULT_TOLERANCES["cut_rate_abs"], DEFAULT_TOLERANCES["cut_rate_rel"] * abs(typ)))
    if kind == "rel":
        return value_range(values, widen=widen, rel=DEFAULT_TOLERANCES[tk])
    return value_range(values, widen=widen, abs_=DEFAULT_TOLERANCES[tk])


def membership(refs: list[dict[str, Any]], facts: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    """For each reference: share of its measured facts outside the ranges built from the other references."""
    out = []
    if len(refs) < 2:
        return out
    for rd in refs:
        me = facts[rd["asset_id"]]
        others = [facts[o["asset_id"]] for o in refs if o["asset_id"] != rd["asset_id"]]
        compared, outside = 0, []
        for k, v in me.items():
            vals = [o[k] for o in others if k in o]
            if not vals:
                continue
            rg = _fact_range(k, vals, widen=len(others) < 3)
            compared += 1
            if not (rg["min"] - 1e-9 <= v <= rg["max"] + 1e-9):
                outside.append(k)
        share = len(outside) / compared if compared else 0.0
        out.append({"asset_id": rd["asset_id"], "compared": compared, "outside": outside, "share_outside": round(share, 3),
                    "warning": compared >= 4 and share > MEMBERSHIP_SHARE})
    return out


# ------------------------------------------------------------------------------------- claim terms
def _claim_weight(c: dict[str, Any]) -> float:
    span = c.get("time_span") or {}
    try:
        return max(1e-3, float(span["end_seconds"]) - float(span["start_seconds"]))
    except (KeyError, TypeError, ValueError):
        return 1.0


def term_support(refs, dim: str) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for rd in refs:
        for c in rd["decided"]:
            if c["eff_dimension"] != dim:
                continue
            s = stats.setdefault(c["eff_term"], {"refs": set(), "weight": 0.0, "kinds": set(), "corrected": False, "claims": []})
            s["refs"].add(rd["asset_id"])
            s["weight"] += _claim_weight(c)
            s["kinds"].add(c["claim_kind"])
            s["corrected"] = s["corrected"] or c["review_status"] == "corrected"
            s["claims"].append(c)
    return stats


def needed_support(n: int) -> int:
    return n if n < 3 else math.ceil(2 * n / 3)


def supported_terms(refs, dim: str) -> dict[str, dict[str, Any]]:
    need = needed_support(len(refs))
    return {t: s for t, s in term_support(refs, dim).items() if len(s["refs"]) >= need}


class Block:
    """Accumulates one block's content and the trust metadata that goes in meta."""

    def __init__(self, name: str, n: int) -> None:
        self.name, self.n = name, n
        self.data: dict[str, Any] = {}
        self.kinds: set[str] = set()
        self.refs: set[str] = set()
        self.corrected = False
        self.brief_used = False
        self.notes: list[str] = []

    def measured(self, key: str, value: Any, refs) -> None:
        if value is None:
            return
        self.data[key] = value
        self.kinds.add("measured")
        self.refs.update(r["asset_id"] for r in refs)

    def from_terms(self, key: str, value: Any, stats: dict[str, dict[str, Any]]) -> None:
        if value in (None, {}, []):
            return
        self.data[key] = value
        for s in stats.values():
            self.kinds.update(s["kinds"])
            self.refs.update(s["refs"])
            self.corrected = self.corrected or s["corrected"]

    def from_brief(self, key: str, value: Any) -> None:
        if value in (None, {}, []):
            return
        self.data[key] = value
        self.brief_used = True
        self.kinds.add("interpreted")

    def meta(self, brief_reviewed: bool) -> dict[str, Any]:
        has_content = any(k != "never" for k in self.data)
        kinds = self.kinds or {"interpreted"}
        if not has_content:
            status = "pending"
        elif self.brief_used and not brief_reviewed:
            status = "pending"
        elif self.corrected:
            status = "corrected"
        else:
            status = "accepted"
        m: dict[str, Any] = {"claim_kind": next(iter(kinds)) if len(kinds) == 1 else "mixed", "review_status": status,
                             "n_refs": max(1, len(self.refs) if self.refs else (self.n if self.brief_used else 1))}
        if has_content and self.n < 3 and "measured" in self.kinds:
            m["provisional"] = True
        missing = [k for k in REQUIRED_V10[self.name] if k not in self.data]
        if missing:
            m["missing"] = missing
        if self.notes:
            m["notes"] = "; ".join(self.notes)[:200]
        return m

    def render(self, brief_reviewed: bool) -> dict[str, Any]:
        out = dict(self.data)
        if self.name in VISUAL_NEVER:
            out.setdefault("never", [])
        out["meta"] = self.meta(brief_reviewed)
        return out


def distribution(stats: dict[str, dict[str, Any]], limit: int = 8) -> dict[str, float]:
    total = sum(s["weight"] for s in stats.values())
    if total <= 0:
        return {}
    items = sorted(((t, s["weight"] / total) for t, s in stats.items()), key=lambda x: (-x[1], x[0]))[:limit]
    return {t: round(v, 3) for t, v in items if round(v, 3) > 0}


def majority_term(stats: dict[str, dict[str, Any]]) -> str | None:
    if not stats:
        return None
    return max(stats.items(), key=lambda kv: (kv[1]["weight"], kv[0]))[0]


# ------------------------------------------------------------------------------------- brief
def load_brief(style_id: str, workspace: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    import jsonschema

    p = style_dir(style_id, workspace) / "brief.json"
    if not p.exists():
        return None, None
    raw = p.read_bytes()
    brief = json.loads(raw.decode("utf-8"))
    schema = json.loads((paths.SCHEMAS_DIR / "style_brief.schema.json").read_text(encoding="utf-8"))
    errs = [f"{'/'.join(str(x) for x in e.path) or '(root)'}: {e.message[:160]}" for e in jsonschema.Draft202012Validator(schema).iter_errors(brief)]
    if brief.get("style_id") != style_id:
        errs.append(f"brief style_id {brief.get('style_id')!r} != {style_id!r}")
    terms = list((brief.get("never") or {}).values()) + [brief.get("never_global") or []]
    for t in [x for lst in terms for x in lst] + [v for v in (brief.get("color") or {}).values()]:
        if not registry.resolve(t):
            errs.append(f"term not in the vocabulary: {t}")
    for rule in brief.get("continuity_rules") or []:
        errs.extend(continuity.rule_problems(rule))
    if errs:
        raise StyleError("brief.json is invalid: " + "; ".join(errs[:12]))
    return brief, _sha(raw)


# ------------------------------------------------------------------------------------- build
def _q_term(dim: str, term: str) -> str:
    return term if dim == "composition" else f"{dim}.{term}"


def _region_shots(refs, region_key: str) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    out = []
    for rd in refs:
        shots = {s["shot_id"]: s for s in _shots(rd)}
        for c in (rd["docs"].get("color") or {}).get("shots", []):
            st = (c.get("regions") or {}).get(region_key)
            if c.get("status") == "ok" and st and st.get("lab_mean") is not None and c["shot_id"] in shots:
                out.append((rd, shots[c["shot_id"]], st))
    return out


def _palette(items: list[tuple[dict, dict, dict]], k: int = 4) -> list[str]:
    weight: dict[str, float] = {}
    for _, shot, st in items:
        for p in st.get("palette") or []:
            weight[p["hex"].upper()] = weight.get(p["hex"].upper(), 0.0) + float(p.get("share") or 0.0) * float(shot.get("duration_s") or 0.0)
    return [h for h, w in sorted(weight.items(), key=lambda kv: (-kv[1], kv[0])) if w > 0][:k]


def _exemplar(rd, shot) -> dict[str, Any]:
    return {"ref": rd["asset_id"], "shot": shot["shot_id"],
            "t": f"{float(shot['t_in']):.2f}-{float(shot['t_out']):.2f}", "frame": int((shot.get("keyframes") or {}).get("mid", shot["frame_first"]))}


def _rule(rule_id, scope, metric, tolerance, severity, rationale, region=None) -> dict[str, Any]:
    r = {"rule_id": rule_id, "scope": scope}
    if region:
        r["region"] = region
    r.update({"metric": metric, "tolerance": tolerance, "severity": severity, "rationale": rationale[:160], "source": "derived"})
    return r


def build(asset_ids: list[str], style_id: str, workspace: Path | None = None) -> dict[str, Any]:
    if not asset_ids:
        raise StyleError("--from needs at least one asset id", "usage")
    if len(set(asset_ids)) != len(asset_ids):
        raise StyleError("--from lists an asset twice", "usage")
    ws = _ws(workspace)
    refs = [load_reference(a, ws) for a in asset_ids]
    n = len(refs)
    widen = n < 3
    tol = DEFAULT_TOLERANCES
    brief, brief_sha = load_brief(style_id, ws)
    brief = brief or {}
    reviewed = bool(brief.get("reviewed_by"))
    facts = {rd["asset_id"]: ref_facts(rd) for rd in refs}
    B = {name: Block(name, n) for name in BLOCKS}

    def fvals(key):
        return [facts[r["asset_id"]][key] for r in refs if key in facts[r["asset_id"]]]

    def frange(key, unit=None, nd=3, lo=None):
        rg = _fact_range(key, fvals(key), widen)
        if rg is None:
            return None
        if lo is not None:
            rg["min"] = max(lo, rg["min"])
        if unit:
            rg["unit"] = unit
        return {k: (_r(v, nd) if isinstance(v, float) else v) for k, v in rg.items()}

    # ---- rhythm
    rh = B["rhythm"]
    rh.measured("duration_s", quantiles(fvals("duration_s"), 2, "s", widen=tol["duration_rel"] * float(np.median(fvals("duration_s"))) if widen and fvals("duration_s") else 0.0), refs)
    hook = {k: v for k, v in {"cuts_in_hook": frange("cuts_in_hook", nd=1, lo=0.0), "first_text_at_s": frange("first_text_at_s", "s", 2, lo=0.0)}.items() if v}
    if hook:
        rh.measured("hook", hook, refs)
    rh.notes.append(f"hook = first {HOOK_S:g} s")
    cut = {k: frange(f"cuts_per_s.{k}", "cuts/s", lo=0.0) for k in ("overall", "hook", "body", "close")}
    if cut["overall"]:
        rh.measured("cut_rate_per_s", {k: v for k, v in cut.items() if v}, refs)
    pooled_len = [float(s["duration_s"]) for rd in refs for s in _shots(rd)]
    if pooled_len:
        w = tol["shot_length_rel"] * float(np.median(pooled_len)) if widen else 0.0
        q = quantiles(pooled_len, 3, "s", widen=w)
        q["min"] = max(0.0, q["min"])
        rh.measured("shot_length_s", q, refs)
    rh.measured("speech_wpm", frange("speech_wpm", "wpm", 1, lo=0.0), refs)
    gaps = fvals("max_silence_gap_s")
    if gaps:
        rh.measured("silence", {"max_gap_s": _r(max(gaps), 2)}, refs)
    onset = fvals("share_cuts_on_onset")
    if onset:
        rh.measured("music_relation", {"share_of_cuts_on_beat": _r(float(np.median(onset)), 3)}, refs)
        rh.notes.append("cuts on beat = cuts within 40 ms of an audio onset")
    reuse = {k: v for k, v in {"unique_pictures": frange("unique_pictures", nd=1, lo=0.0), "reuse_factor": frange("reuse_factor", lo=1.0)}.items() if v}
    if reuse:
        rh.measured("image_reuse", reuse, refs)

    # ---- camera
    cam = B["camera"]
    st = supported_terms(refs, "camera.movement")
    cam.from_terms("movement", distribution(st), st)
    st_opt = supported_terms(refs, "optics")
    dof = {t: s for t, s in st_opt.items() if t in ("shallow_depth_of_field", "deep_focus")}
    lens = {t: s for t, s in st_opt.items() if t not in dof}
    optics = {}
    if dof:
        optics["depth_of_field"] = _q_term("optics", majority_term(dof))
    if lens:
        optics["lens_look"] = [_q_term("optics", t) for t in sorted(lens, key=lambda t: -lens[t]["weight"])[:4]]
    cam.from_terms("optics", optics, st_opt)

    # ---- light
    li = B["light"]
    for key, dim in (("key", "light.key"), ("edge", "light.quality")):
        s = supported_terms(refs, dim)
        t = majority_term(s)
        li.from_terms(key, _q_term(dim, t) if t else None, s)
    s = supported_terms(refs, "light.direction")
    li.from_terms("direction", distribution(s), s)
    cr_vals = [c["light"]["contrast_ratio_p95_p5"] for rd in refs for c in (rd["docs"].get("color") or {}).get("shots", [])
               if c.get("status") == "ok" and (c.get("light") or {}).get("contrast_ratio_p95_p5") is not None]
    li.measured("contrast_ratio", value_range(cr_vals, widen=widen, rel=tol["contrast_rel"], nd=2, lo=1.0), refs)
    s = supported_terms(refs, "light.scheme")
    if s:
        li.from_terms("scheme", [_q_term("light.scheme", t) for t in sorted(s, key=lambda t: -s[t]["weight"])[:3]], s)

    # ---- color
    co = B["color"]
    for key in ("grade_family", "temperature"):
        dim = f"color.{key}"
        s = supported_terms(refs, dim)
        t = majority_term(s)
        if t:
            co.from_terms(key, _q_term(dim, t), s)
        elif (brief.get("color") or {}).get(key):
            co.from_brief(key, brief["color"][key])
    regions = {}
    for name, key in continuity.REGION_KEYS.items():
        items = _region_shots(refs, key)
        if not items:
            continue
        labs = np.array([st_["lab_mean"] for _, _, st_ in items], dtype=float)
        reg = {"L": value_range(labs[:, 0], widen=widen, abs_=tol["L_abs"], nd=1, lo=0.0, hi=100.0),
               "a": value_range(labs[:, 1], widen=widen, abs_=tol["ab_abs"], nd=1),
               "b": value_range(labs[:, 2], widen=widen, abs_=tol["ab_abs"], nd=1),
               "saturation": saturation_class(float(np.median([st_.get("sat_mean") or 0.0 for _, _, st_ in items])))}
        pal = _palette(items)
        if pal:
            reg["palette"] = pal
        if name != "frame":
            reg["share_of_frame"] = value_range([st_.get("coverage") or 0.0 for _, _, st_ in items], widen=widen, abs_=tol["share_abs"], nd=2, lo=0.0, hi=1.0)
        regions[name] = reg
    co.measured("regions", regions or None, refs)
    co.notes.append(f"saturation classes: mean saturation < {SAT_CLASSES[0][0]} low, < {SAT_CLASSES[1][0]} medium, < {SAT_CLASSES[2][0]} medium_high")
    bg_cov = [st_.get("coverage") or 0.0 for _, _, st_ in _region_shots(refs, "background")]
    master_region = "background" if bg_cov and float(np.median(bg_cov)) >= MASTER_MIN_COVERAGE else ("frame" if "frame" in regions else None)
    probe_bible = {"color": {"regions": regions}}
    de_units: list[tuple[dict, dict]] = []
    if master_region:
        for rd in refs:
            for u in continuity.units_delta_e(rd["docs"], {"region": master_region}, probe_bible) or []:
                de_units.append((rd, u))
        de = [u["value"] for _, u in de_units]
        co.measured("delta_e_between_shots", quantiles(de, 2, "dE00", widen=tol["delta_e_abs"] if widen else 0.0), refs)
        if co.data.get("delta_e_between_shots"):
            co.data["delta_e_between_shots"]["min"] = max(0.0, co.data["delta_e_between_shots"]["min"])
        co.notes.append(f"delta E: each shot's {master_region} mean vs the style's typical {master_region}")

    # ---- composition
    cp = B["composition"]
    s = supported_terms(refs, "composition")
    cp.from_terms("techniques", distribution(s), s)

    # ---- environment
    en = B["environment"]
    s = supported_terms(refs, "material.surface")
    if s:
        en.from_terms("surfaces", [_q_term("material.surface", t) for t in sorted(s, key=lambda t: -s[t]["weight"])[:8]], s)
    s = supported_terms(refs, "material_atmosphere")
    if s:
        en.from_terms("atmosphere", [_q_term("material_atmosphere", t) for t in sorted(s, key=lambda t: -s[t]["weight"])[:6]], s)
    for key in ("settings", "props_recurring", "clutter_level"):
        en.from_brief(key, (brief.get("environment") or {}).get(key))

    # ---- assets
    B["assets"].from_brief("families", (brief.get("assets") or {}).get("families"))

    # ---- typography and animation
    ty, an = B["typography"], B["animation"]
    s = supported_terms(refs, "typography.family_class")
    t = majority_term(s)
    ty.from_terms("family_class", _q_term("typography.family_class", t) if t else None, s)
    text_refs = [rd for rd in refs if _caps(rd)]
    if text_refs:
        caps = [(rd, c) for rd in text_refs for c in _caps(rd)]
        letters = "".join(ch for _, c in caps for ch in (c.get("text") or "") if ch.isalpha())
        if letters:
            up = sum(ch.isupper() for ch in letters) / len(letters)
            words = [w for _, c in caps for w in (c.get("text") or "").split() if w[:1].isalpha()]
            capitalized = (sum(w[0].isupper() for w in words) / len(words)) if words else 0.0
            inner_up = sum(ch.isupper() for w in words for ch in w[1:] if ch.isalpha())
            case = ("upper" if up > 0.9 else "lower" if up < 0.02 else "mixed" if capitalized > 0.6 or inner_up > 0.1 * len(letters) else "sentence")
            ty.measured("case", case, text_refs)
        ty.measured("size_rel_frame_h", value_range([c["rel_height"] for _, c in caps], widen=widen, rel=tol["type_size_rel"], nd=4, lo=0.0,
                                                    spread=(10, 90)), text_refs)
        zones: dict[str, int] = {}
        for _, c in caps:
            zones[c["zone"]] = zones.get(c["zone"], 0) + 1
        zone = max(zones.items(), key=lambda kv: (kv[1], kv[0]))[0]
        ty.measured("placement", {"zone": ZONE_TO_PLACEMENT.get(zone, "center")}, text_refs)
        cues = [(rd, b) for rd in text_refs for b in _blocks(rd) or []]
        max_lines = max([b["lines"] for _, b in cues], default=1)
        cpl = [len(c.get("text") or "") for _, c in caps]
        ty.measured("lines", {"max": int(min(4, max_lines)), "chars_per_line_p90": int(np.percentile(cpl, 90))}, text_refs)
        build_on = sum(1 for _, c in caps if c.get("animation") == "build_on")
        if build_on:
            ty.data["emphasis"] = {"word_reveal": round(build_on / len(caps), 3)}
            ty.kinds.add("estimated")
            ty.notes.append("emphasis word_reveal = share of caption tracks that grow word by word in OCR")
        cad = {"cues_per_10s": frange("cues_per_10s", "cues", 2, lo=0.0),
               "cue_duration_s": value_range([_cap_duration_s(b, rd["fps"]) for rd, b in cues], widen=widen, rel=tol["hold_rel"], nd=2, lo=0.0, unit="s", spread=(10, 90)),
               "words_per_cue": value_range([b["words"] for _, b in cues], widen=widen, abs_=tol["words_abs"], nd=1, lo=0.0, spread=(10, 90))}
        leads = [x for rd in text_refs for x in caption_leads_ms(rd)]
        if leads:
            cad["lead_vs_speech_ms"] = value_range(leads, widen=widen, abs_=tol["lead_ms_abs"], nd=0, unit="ms", spread=(10, 90))
        ty.measured("caption_cadence", {k: v for k, v in cad.items() if v}, text_refs)
        an.measured("hold_ms", value_range([_cap_duration_s(b, rd["fps"]) * 1000 for rd, b in cues], widen=widen, rel=tol["hold_rel"], nd=0, lo=0.0,
                                           unit="ms", spread=(10, 90)), text_refs)
        an.notes.append("hold = caption cue (block of lines) on screen, from OCR samples")
    elif any((rd["docs"].get("coverage") or {}).get("stages", {}).get("text", {}).get("status") != "ok" for rd in refs):
        ty.notes.append("text stage did not run on every reference")

    # ---- montage
    mo = B["montage"]
    trans: dict[str, float] = {}
    for rd in refs:
        for s_ in _shots(rd):
            term = TRANSITION_TERMS.get(s_.get("transition_in"))
            if term:
                trans[term] = trans.get(term, 0) + 1
    if trans:
        tot = sum(trans.values())
        mo.measured("transitions", {k: round(v / tot, 3) for k, v in sorted(trans.items(), key=lambda kv: -kv[1])}, refs)
        mo.kinds.discard("measured")
        mo.kinds.add("estimated")

    # ---- sound
    so = B["sound"]
    so.measured("loudness_lufs", frange("loudness_lufs", "LUFS", 1), [r for r in refs if _audio(r)])
    tp = fvals("true_peak_dbtp")
    if tp:
        so.measured("true_peak_dbtp_max", _r(max(tp) + (tol["true_peak_abs"] if widen else 0.0), 1), [r for r in refs if _audio(r)])
    s = supported_terms(refs, "sound.role")
    so.from_terms("role", distribution(s), s)
    so.from_brief("voice_treatment", (brief.get("sound") or {}).get("voice_treatment"))
    if not any(_audio(r) for r in refs):
        so.notes.append("no reference has an analysed audio track")

    # ---- narrative
    na = B["narrative"]
    per_ref_structure = []
    for rd in refs:
        cl = sorted([c for c in rd["decided"] if c["eff_dimension"] == "narrative.function"], key=lambda c: (c.get("time_span") or {}).get("start_seconds", 0))
        seq: list[str] = []
        for c in cl:
            if not seq or seq[-1] != c["eff_term"]:
                seq.append(c["eff_term"])
        if seq:
            per_ref_structure.append(tuple(seq[:8]))
    if per_ref_structure:
        counts: dict[tuple, int] = {}
        for sq in per_ref_structure:
            counts[sq] = counts.get(sq, 0) + 1
        best, cnt = max(counts.items(), key=lambda kv: (kv[1], len(kv[0])))
        if cnt >= needed_support(n) and len(best) >= 2:
            na.from_terms("structure", [_q_term("narrative.function", t) for t in best], supported_terms(refs, "narrative.function") or term_support(refs, "narrative.function"))
        else:
            na.notes.append("narrative order differs between references")
    s = supported_terms(refs, "narrative.function")
    na.from_terms("beat_share_of_runtime", distribution(s), s)
    s = supported_terms(refs, "narrative.hook_type")
    if s:
        na.from_terms("hook_type", [_q_term("narrative.hook_type", t) for t in sorted(s, key=lambda t: -s[t]["weight"])[:3]], s)
    na.from_brief("cta_treatment", (brief.get("narrative") or {}).get("cta_treatment"))

    # ---- identity and concept
    idt = B["identity"]
    tech = supported_terms(refs, "composition")
    if tech:
        idt.from_terms("signature_techniques", sorted(tech, key=lambda t: -tech[t]["weight"])[:6], tech)
    for key in ("one_line", "iris_operations", "tone_words"):
        idt.from_brief(key, (brief.get("identity") or {}).get(key))
    for key in ("visual_concept", "metaphor_language", "subject_treatment", "viewer_promise"):
        B["concept"].from_brief(key, (brief.get("concept") or {}).get(key))

    # ---- never lists (brief only)
    for name, terms in (brief.get("never") or {}).items():
        B[name].data["never"] = [registry.resolve(t).qualified if registry.resolve(t).dimension != "composition" else registry.resolve(t).term for t in terms]
        B[name].brief_used = True

    # ---- continuity rules from the tightest measured ranges
    rules: list[dict[str, Any]] = []
    if de_units:
        de = np.array([u["value"] for _, u in de_units])
        p90 = float(np.percentile(de, 90))
        if p90 <= 8.0:
            floor = DELTA_E_FLOOR_PROVISIONAL if widen else DELTA_E_FLOOR
            limit = round(min(DELTA_E_CEILING, max(floor, p90 + tol["delta_e_abs"])), 1)
            rules.append(_rule(f"cr_{master_region}_delta_e", "every_shot", "color.delta_e2000_vs_style", f"<= {limit}", "fail",
                               f"{master_region} colour stays near the style's typical value (refs p90 {p90:.1f})", master_region))
    if "frame" in regions:
        L = regions["frame"]["L"]
        if L["max"] - L["min"] <= 30:
            rules.append(_rule("cr_frame_luma", "every_shot", "color.L_mean", f"within [{L['min']:g}, {L['max']:g}]", "warn",
                               "overall brightness of each shot stays in the style's band", "frame"))
    for dim, metric, rid in (("light.side", "light.side", "cr_light_side"), ("light.key", "light.key", "cr_light_key")):
        stt = supported_terms(refs, dim)
        dist_ = distribution(stt)
        top = [t for t, _ in sorted(dist_.items(), key=lambda kv: -kv[1])[:2]]
        if top and sum(dist_[t] for t in top) >= 0.9:
            rules.append(_rule(rid, "every_shot", metric, "in {" + ", ".join(sorted(top)) + "}", "warn",
                               f"accepted {dim} labels concentrate on these terms"))
    if pooled_len:
        mx = max(pooled_len) * (1 + tol["shot_length_rel"])
        rules.append(_rule("cr_shot_length", "every_shot", "rhythm.shot_length_s", f"<= {round(mx, 2):g}", "warn", "no shot holds longer than the style allows"))
    if cut["overall"]:
        rules.append(_rule("cr_cut_rate", "sequence", "montage.cuts_per_s", f"within [{cut['overall']['min']:g}, {cut['overall']['max']:g}]", "warn",
                           "cutting rate stays in the style's band"))
    if text_refs:
        zshare = max(zones.values()) / sum(zones.values())
        if zshare >= 0.8:
            rules.append(_rule("cr_caption_zone", "text_layers", "typography.zone", "in {" + zone + "}", "warn", "captions keep their zone"))
        sz = ty.data.get("size_rel_frame_h")
        if sz and sz["typical"] > 0 and (sz["max"] - sz["min"]) / sz["typical"] <= 0.8:
            rules.append(_rule("cr_caption_size", "text_layers", "typography.size_rel_frame_h", f"within [{sz['min']:g}, {sz['max']:g}]", "warn",
                               "caption line height stays in the style's band"))
    lufs = so.data.get("loudness_lufs")
    if lufs:
        rules.append(_rule("cr_loudness", "audio", "audio.integrated_lufs", f"within [{lufs['min']:g}, {lufs['max']:g}]", "fail", "integrated loudness matches the style"))
    if "true_peak_dbtp_max" in so.data:
        rules.append(_rule("cr_true_peak", "audio", "audio.true_peak_dbtp", f"<= {so.data['true_peak_dbtp_max']:g}", "warn", "true peak stays under the style's ceiling"))
    seen = {r["rule_id"] for r in rules}
    for r in brief.get("continuity_rules") or []:
        if r["rule_id"] not in seen:
            rules.append({**r, "source": "brief"})
            seen.add(r["rule_id"])
    rules = rules[:20]
    if len(rules) < 3:
        raise StyleError(f"only {len(rules)} continuity rule(s) could be derived; a Style Bible needs at least 3 (add rules in brief.json)", "validation")

    # ---- exemplars
    ex: dict[str, list[dict[str, Any]]] = {}
    if de_units:
        rd, u = min(de_units, key=lambda x: x[1]["value"])
        shot = next(s_ for s_ in _shots(rd) if s_["shot_id"] == u["shot_id"])
        ex["color_master"] = [_exemplar(rd, shot)]
    else:
        raise StyleError("no colour measurements in any reference: the color stage must run before style build")
    hook_vals = fvals("cuts_per_s.hook")
    if hook_vals:
        med = float(np.median(hook_vals))
        rd = min(refs, key=lambda r: abs(facts[r["asset_id"]].get("cuts_per_s.hook", 1e9) - med))
        ex["hook"] = [_exemplar(rd, _shots(rd)[0])]
    cr_items = [(rd, c) for rd in refs for c in (rd["docs"].get("color") or {}).get("shots", [])
                if c.get("status") == "ok" and (c.get("light") or {}).get("contrast_ratio_p95_p5") is not None]
    if cr_items:
        med = float(np.median([c["light"]["contrast_ratio_p95_p5"] for _, c in cr_items]))
        rd, c = min(cr_items, key=lambda x: abs(x[1]["light"]["contrast_ratio_p95_p5"] - med))
        ex["light_master"] = [_exemplar(rd, next(s_ for s_ in _shots(rd) if s_["shot_id"] == c["shot_id"]))]
    if text_refs:
        caps_all = [(rd, c) for rd in text_refs for c in _caps(rd)]
        med = float(np.median([c["rel_height"] for _, c in caps_all]))
        rd, c = min(caps_all, key=lambda x: abs(x[1]["rel_height"] - med))
        shot = next((s_ for s_ in _shots(rd) if s_["frame_first"] <= c["frame_first_seen"] <= s_["frame_last_inclusive"]), _shots(rd)[0])
        ex["caption_style"] = [_exemplar(rd, shot)]
    mv = cam.data.get("movement")
    if mv:
        dom = max(mv.items(), key=lambda kv: kv[1])[0]
        cl = [(rd, c) for rd in refs for c in rd["decided"] if c["eff_dimension"] == "camera.movement" and c["eff_term"] == dom]
        if cl:
            rd, c = max(cl, key=lambda x: _claim_weight(x[1]))
            shot = next((s_ for s_ in _shots(rd) if s_["shot_id"] == c.get("unit_id")), None)
            if shot:
                ex["camera_signature"] = [_exemplar(rd, shot)]
    tr_shots = [(rd, s_) for rd in refs for s_ in _shots(rd) if s_.get("transition_in") in ("fade_in", "fade_out", "dissolve_candidate")]
    if tr_shots:
        ex["transition_signature"] = [_exemplar(*tr_shots[0])]

    # ---- assemble
    cov_states = [rd["docs"]["coverage"] for rd in refs]
    model_exposed = any(isinstance(c.get("model_exposure"), dict) and c["model_exposure"].get("judge") not in (None, "fixture") for c in cov_states)
    not_ok = sorted({f"{name}:{st_['status']}" for c in cov_states for name, st_ in (c.get("stages") or {}).items() if st_.get("status") not in ("ok",)})
    store = Store(ws)
    try:
        claim_ids = set().union(*[rd["claim_ids"] for rd in refs])
        events = [e for e in store.review_events() if e.get("claim_id") in claim_ids]
    finally:
        store.close()
    bible: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "style_id": style_id, "status": "draft", "language": "en", "built_from": asset_ids,
        "coverage_summary": {"decode": "full" if all(c.get("decode") == "full" for c in cov_states) else "partial",
                             "measurement": "full" if all(c.get("measurement") == "full" for c in cov_states) else "partial",
                             "model_exposure": "economy" if model_exposed else "none"},
    }
    if not_ok:
        bible["coverage_summary"]["notes"] = ("stages not ok: " + ", ".join(not_ok))[:300]
    for name in BLOCKS:
        bible[name] = B[name].render(reviewed)
    bible["continuity_rules"] = rules
    never_global = [registry.resolve(t).qualified if registry.resolve(t).dimension != "composition" else registry.resolve(t).term for t in brief.get("never_global") or []]
    bible["never_global"] = never_global
    bible["exemplars"] = ex
    prov: dict[str, Any] = {"generated_at": _now(), "iris_version": __version__, "vocabulary_version": registry.vocabulary_version(),
                            "review_events_sha256": _sha(_canon(events)), "inputs_sha256": {rd["asset_id"]: rd["inputs_sha256"] for rd in refs}}
    if widen:
        prov["default_tolerances"] = dict(tol)
    if brief_sha:
        prov["brief_sha256"] = brief_sha
    bible["provenance"] = prov
    bible["token_budget"] = {"limit": TOKEN_LIMIT, "measured": 0, "tokenizer": TOKENIZER}
    trimmed = fit_budget(bible)
    bible["token_budget"]["measured"] = measure_tokens(bible)
    bible["token_budget"]["measured"] = measure_tokens(bible)
    if bible["token_budget"]["measured"] > TOKEN_LIMIT:
        raise StyleError(f"Style Bible needs {bible['token_budget']['measured']} tokens after trimming {trimmed}; the limit is {TOKEN_LIMIT}")

    out_dir = style_dir(style_id, ws)
    out_dir.mkdir(parents=True, exist_ok=True)
    sha = write_bible(out_dir, bible)
    mem = membership(refs, facts)
    report = {"ok": True, "style_id": style_id, "status": bible["status"], "built_from": asset_ids, "n_refs": n, "provisional": widen,
              "tokens": bible["token_budget"]["measured"], "token_limit": TOKEN_LIMIT, "sha256": sha,
              "continuity_rules": len(rules), "rules": [r["rule_id"] for r in rules],
              "blocks": {name: {k: bible[name]["meta"].get(k) for k in ("claim_kind", "review_status", "n_refs", "provisional", "missing") if k in bible[name]["meta"]} for name in BLOCKS},
              "pending_blocks": [name for name in BLOCKS if bible[name]["meta"]["review_status"] == "pending"],
              "brief": "reviewed" if reviewed else ("unreviewed" if brief_sha else "absent"),
              "membership": mem, "membership_warnings": [m["asset_id"] for m in mem if m["warning"]],
              "decided_claims_used": sum(len(rd["decided"]) for rd in refs),
              "files": {k: str(out_dir / v) for k, v in (("json", "style_bible.json"), ("md", "style_bible.md"), ("sha256", "style_bible.sha256"))}}
    if trimmed:
        report["trimmed_for_budget"] = trimmed
    if not brief_sha:
        report["brief_template"] = str(paths.SCHEMAS_DIR / "examples" / "style_brief.example.json")
    (out_dir / "build_report.json").write_text(json.dumps({**report, "generated_at": _now(), "method_version": METHOD_VERSION}, indent=1), encoding="utf-8")
    issues = lint(style_id, ws)["issues"]
    if issues:
        report["ok"] = False
        report["lint_issues"] = issues
    return report


# ------------------------------------------------------------------------------------- files
def fit_budget(bible: dict[str, Any]) -> list[str]:
    """Drop the least load-bearing detail until the bible fits. rhythm, continuity_rules and never lists
    are never trimmed (docs/style_bible.md rule 6). Returns what was dropped, in order."""
    dropped: list[str] = []
    regions = (bible.get("color") or {}).get("regions") or {}
    steps: list[tuple[str, Any]] = []
    for reg in ("graphics", "skin", "subject", "frame"):
        steps.append((f"color.regions.{reg}.palette", lambda r=reg: regions.get(r, {}).pop("palette", None)))
    for reg in ("graphics", "skin", "subject", "background"):
        steps.append((f"color.regions.{reg}.share_of_frame", lambda r=reg: regions.get(r, {}).pop("share_of_frame", None)))
    for name in BLOCKS:
        steps.append((f"{name}.meta.notes", lambda n=name: bible[n]["meta"].pop("notes", None)))
    steps.append(("continuity_rules.rationale", lambda: [r.pop("rationale", None) for r in bible["continuity_rules"]] and None))
    for kind in ("transition_signature", "light_master", "camera_signature"):
        steps.append((f"exemplars.{kind}", lambda k=kind: bible["exemplars"].pop(k, None)))
    for label, fn in steps:
        if measure_tokens(bible) <= TOKEN_LIMIT - 10:
            break
        before = measure_tokens(bible)
        fn()
        if measure_tokens(bible) < before:
            dropped.append(label)
    return dropped


def measure_tokens(bible: dict[str, Any]) -> int:
    return int(math.ceil(len(json.dumps(bible, separators=(",", ":"), ensure_ascii=False)) / CHARS_PER_TOKEN))


def bible_bytes(bible: dict[str, Any]) -> bytes:
    return (json.dumps(bible, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def write_bible(out_dir: Path, bible: dict[str, Any]) -> str:
    data = bible_bytes(bible)
    (out_dir / "style_bible.json").write_bytes(data)
    (out_dir / "style_bible.md").write_text(render_md(bible), encoding="utf-8")
    sha = _sha(data)
    (out_dir / "style_bible.sha256").write_text(sha + "\n", encoding="utf-8")
    return sha


def load_bible(style_id: str, workspace: Path | None = None) -> dict[str, Any]:
    p = style_dir(style_id, workspace) / "style_bible.json"
    if not p.exists():
        raise StyleError(f"no Style Bible for {style_id}: run `iris style build` first", "validation")
    return json.loads(p.read_text(encoding="utf-8"))


def _fmt(v: Any) -> str:
    if isinstance(v, dict):
        if {"min", "max"} <= set(v) and not ({"p25", "p50"} & set(v)):
            s = f"{v['min']:g} to {v['max']:g}"
            if "typical" in v:
                s += f" (typical {v['typical']:g})"
            return s + (f" {v['unit']}" if v.get("unit") else "")
        if {"p25", "p50", "p75"} <= set(v):
            parts = [f"{k} {v[k]:g}" for k in ("min", "p25", "p50", "p75", "max") if k in v]
            return ", ".join(parts) + (f" {v['unit']}" if v.get("unit") else "")
        if v and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v.values()):
            return ", ".join(f"{k} {x:g}" for k, x in v.items())
        return ""
    if isinstance(v, list):
        return ", ".join(_fmt(x) if isinstance(x, dict) else str(x) for x in v) if v else "(none)"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _md_obj(obj: dict[str, Any], indent: int, lines: list[str]) -> None:
    pad = "  " * indent
    for k, v in obj.items():
        if k == "meta":
            continue
        flat = _fmt(v)
        if isinstance(v, dict) and not flat:
            lines.append(f"{pad}- **{k}**")
            _md_obj(v, indent + 1, lines)
        elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v) and not all({"min", "max"} <= set(x) for x in v):
            lines.append(f"{pad}- **{k}**")
            for x in v:
                lines.append(f"{pad}  - " + "; ".join(f"{kk}: {_fmt(vv)}" for kk, vv in x.items()))
        else:
            lines.append(f"{pad}- **{k}**: {flat}")


def render_md(bible: dict[str, Any]) -> str:
    """Deterministic Markdown view of the JSON. Never edited by hand; `lint` checks the round trip."""
    lines = [f"# Style Bible: {bible['style_id']}", "",
             f"Status: {bible['status']}. Built from {len(bible['built_from'])} reference(s): {', '.join(bible['built_from'])}. "
             f"Schema {bible['schema_version']}, vocabulary {bible['provenance']['vocabulary_version']}.", "",
             "Generated from style_bible.json; do not edit.", ""]
    cs = bible["coverage_summary"]
    lines += [f"Coverage: decode {cs['decode']}, measurement {cs['measurement']}, model exposure {cs['model_exposure']}." + (f" {cs['notes']}" if cs.get("notes") else ""), ""]
    for name in BLOCKS:
        blk = bible[name]
        m = blk["meta"]
        lines.append(f"## {name}")
        trust = f"{m['claim_kind']}, {m['review_status']}, {m['n_refs']} ref(s)" + (", provisional" if m.get("provisional") else "")
        lines.append(f"_{trust}_")
        if m.get("missing"):
            lines.append(f"_missing: {', '.join(m['missing'])}_")
        if m.get("notes"):
            lines.append(f"_notes: {m['notes']}_")
        lines.append("")
        _md_obj(blk, 0, lines)
        lines.append("")
    lines.append("## continuity_rules")
    lines.append("")
    for r in bible["continuity_rules"]:
        where = f" [{r['region']}]" if r.get("region") else ""
        lines.append(f"- `{r['rule_id']}` ({r['severity']}, {r['scope']}{where}): {r['metric']} {r['tolerance']}" + (f". {r['rationale']}" if r.get("rationale") else ""))
    lines += ["", "## never_global", "", f"- {_fmt(bible['never_global'])}", "", "## exemplars", ""]
    for k, lst in bible["exemplars"].items():
        lines.append(f"- **{k}**: " + "; ".join(f"{e['ref']} {e['shot']} t {e.get('t', '?')} frame {e.get('frame', '?')}" for e in lst))
    p = bible["provenance"]
    lines += ["", "## provenance", "", f"- generated_at: {p['generated_at']}", f"- iris_version: {p['iris_version']}",
              f"- review_events_sha256: {p['review_events_sha256']}"]
    if p.get("approved_by"):
        lines.append(f"- approved_by: {p['approved_by']} at {p.get('approved_at')}")
    if p.get("default_tolerances"):
        lines.append("- default_tolerances: " + ", ".join(f"{k} {v:g}" for k, v in p["default_tolerances"].items()))
    tb = bible["token_budget"]
    lines += ["", f"Tokens: {tb['measured']} of {tb['limit']} ({tb['tokenizer']}).", ""]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------- lint
TERM_FIELDS = [("identity", "signature_techniques"), ("camera", "optics", "depth_of_field"), ("camera", "optics", "lens_look"), ("light", "key"),
               ("light", "edge"), ("light", "scheme"), ("color", "grade_family"), ("color", "temperature"), ("environment", "surfaces"),
               ("environment", "atmosphere"), ("typography", "family_class"), ("narrative", "structure"), ("narrative", "hook_type"),
               ("rhythm", "music_relation", "term")]


def _get(obj: Any, path: tuple[str, ...]) -> Any:
    for k in path:
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def lint(style_id: str, workspace: Path | None = None) -> dict[str, Any]:
    import jsonschema

    ws = _ws(workspace)
    d = style_dir(style_id, ws)
    issues: list[str] = []
    bible = load_bible(style_id, ws)
    data = (d / "style_bible.json").read_bytes()
    schema = json.loads((paths.SCHEMAS_DIR / "style_bible.schema.json").read_text(encoding="utf-8"))
    for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(bible), key=lambda e: list(e.path)):
        issues.append(f"schema: {'/'.join(str(x) for x in e.path) or '(root)'}: {e.message[:160]}")
    if bible.get("style_id") != style_id:
        issues.append(f"style_id {bible.get('style_id')!r} != directory {style_id!r}")
    vmaj = str(bible.get("provenance", {}).get("vocabulary_version", "")).split(".")[0]
    if vmaj != registry.vocabulary_version().split(".")[0]:
        issues.append(f"vocabulary major version {vmaj} != {registry.vocabulary_version()}")
    terms: list[str] = []
    for path in TERM_FIELDS:
        v = _get(bible, path)
        if v is not None:
            terms += v if isinstance(v, list) else [v]
    for name in VISUAL_NEVER + ["sound"]:
        terms += (bible.get(name) or {}).get("never") or []
    terms += bible.get("never_global") or []
    for t in terms:
        if not registry.resolve(t):
            issues.append(f"term not in the vocabulary: {t}")
    for (blk, field), dim in DIST_DIMS.items():
        dist_ = _get(bible, (blk, field)) or {}
        valid = set(registry.term_ids(dim))
        for k in dist_:
            if k not in valid:
                issues.append(f"{blk}.{field}: key {k!r} is not a {dim} term")
    for r in bible.get("continuity_rules") or []:
        issues.extend(continuity.rule_problems(r))
    for kind, lst in (bible.get("exemplars") or {}).items():
        for e in lst:
            shots_p = ws / "refs" / e["ref"] / "shots.json"
            if not shots_p.exists():
                issues.append(f"exemplar {kind}: {e['ref']} has no shots.json in this workspace")
                continue
            ids = {s["shot_id"] for s in json.loads(shots_p.read_text(encoding="utf-8")).get("shots", [])}
            if e["shot"] not in ids:
                issues.append(f"exemplar {kind}: {e['ref']} has no shot {e['shot']}")
    tokens = measure_tokens(bible)
    if tokens > TOKEN_LIMIT:
        issues.append(f"token budget exceeded: {tokens} > {TOKEN_LIMIT}")
    if abs(tokens - int(bible.get("token_budget", {}).get("measured", -1))) > 2:
        issues.append(f"token_budget.measured {bible.get('token_budget', {}).get('measured')} != recomputed {tokens}")
    md_p = d / "style_bible.md"
    if not md_p.exists() or md_p.read_text(encoding="utf-8") != render_md(bible):
        issues.append("style_bible.md is not the rendering of style_bible.json (regenerate, never edit by hand)")
    sha_p = d / "style_bible.sha256"
    if not sha_p.exists() or sha_p.read_text(encoding="utf-8").strip() != _sha(data):
        issues.append("style_bible.sha256 does not match style_bible.json")
    if bible.get("status") == "approved":
        issues.extend(approval_blockers(bible))
    return {"ok": not issues, "style_id": style_id, "status": bible.get("status"), "tokens": tokens, "token_limit": TOKEN_LIMIT,
            "sha256": _sha(data), "issues": issues}


def approval_blockers(bible: dict[str, Any]) -> list[str]:
    out = []
    if len(bible.get("built_from") or []) < 3:
        out.append(f"approval needs at least 3 references (has {len(bible.get('built_from') or [])})")
    for name in BLOCKS:
        m = (bible.get(name) or {}).get("meta") or {}
        if m.get("provisional"):
            out.append(f"block {name} is provisional")
        if m.get("review_status") == "pending":
            out.append(f"block {name} is pending review")
    return out


def approve(style_id: str, author: str, workspace: Path | None = None) -> dict[str, Any]:
    if not author:
        raise StyleError("approve needs --author", "usage")
    ws = _ws(workspace)
    res = lint(style_id, ws)
    if not res["ok"]:
        return {"ok": False, "style_id": style_id, "status": res["status"], "blockers": res["issues"]}
    bible = load_bible(style_id, ws)
    blockers = approval_blockers(bible)
    if blockers:
        return {"ok": False, "style_id": style_id, "status": bible["status"], "blockers": blockers}
    bible["status"] = "approved"
    bible["provenance"]["approved_by"] = author
    bible["provenance"]["approved_at"] = _now()
    bible["token_budget"]["measured"] = measure_tokens(bible)
    sha = write_bible(style_dir(style_id, ws), bible)
    res = lint(style_id, ws)
    return {"ok": res["ok"], "style_id": style_id, "status": "approved", "sha256": sha, "issues": res["issues"]}
