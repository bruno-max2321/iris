"""Evidence index and code-sourced claims.

Every claim cites evidence ids. The index maps each id to where the value lives (file, pointer) so
`validate` can reject a citation that points nowhere and a report can navigate from a conclusion to its
measurement. Code claims are the `estimated` labels the measurement stages already produce (camera
class, light key / side / quality, caption cadence, montage pacing), expressed in vocabulary terms."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import registry

EVIDENCE_VERSION = "evidence@0.1.0"
STAGE_FILES = ["index", "shots", "events", "motion", "color", "text", "audio", "sheets", "coverage"]


def _read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def load_docs(ref_dir: Path) -> dict[str, Any]:
    docs: dict[str, Any] = {}
    for name in STAGE_FILES:
        p = ref_dir / f"{name}.json"
        docs[name] = _read(p) if p.exists() else None
    return docs


# ------------------------------------------------------------------------------------------ index
def build_index(docs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}

    def put(eid: str, file: str, pointer: str, value: Any = None, kind: str = "value") -> None:
        idx[eid] = {"kind": kind, "file": file, "pointer": pointer, "value": value}

    shots = (docs.get("shots") or {}).get("shots", [])
    for s in shots:
        sid = s["shot_id"]
        put(f"shot:{sid}", "shots.json", f"shots[{sid}]", {k: s.get(k) for k in ("t_in", "t_out", "duration_s", "frame_first", "frame_last_inclusive", "transition_in")})
        for which in ("first", "mid", "last", "sharpest"):
            fid = (s.get("keyframes") or {}).get(which)
            if fid is not None:
                put(f"keyframe:{sid}:{which}", "shots.json", f"shots[{sid}].keyframes.{which}", {"frame_id": fid}, kind="frame")
    montage = (docs.get("shots") or {}).get("montage") or {}
    for k, v in montage.items():
        put(f"montage:{k}", "shots.json", f"montage.{k}", v)
    for e in (docs.get("events") or {}).get("events", []):
        put(f"event:{e['event_id']}", "events.json", f"events[{e['event_id']}]", {k: e.get(k) for k in ("type", "t_in", "t_out", "length_frames")})
    for m in (docs.get("motion") or {}).get("shots", []):
        sid = m["shot_id"]
        for k, v in m.items():
            if k in ("shot_id", "alternatives", "claim_kind", "status"):
                continue
            put(f"motion:{sid}:{k}", "motion.json", f"shots[{sid}].{k}", v)
    for c in (docs.get("color") or {}).get("shots", []):
        sid = c["shot_id"]
        light = c.get("light") or {}
        for k, v in light.items():
            if k == "claim_kind":
                continue
            put(f"light:{sid}:{k}", "color.json", f"shots[{sid}].light.{k}", v)
        for region, stats in (c.get("regions") or {}).items():
            if not stats:
                continue
            for k in ("palette", "lab_mean", "delta_e2000_vs_master", "delta_e2000_vs_prev", "coverage", "sat_mean"):
                if k in stats:
                    put(f"color:{sid}:{region}:{k}", "color.json", f"shots[{sid}].regions.{region}.{k}", stats[k])
    for t in (docs.get("text") or {}).get("tracks", []):
        put(f"text:{t['track_id']}", "text.json", f"tracks[{t['track_id']}]", {k: t.get(k) for k in ("text", "conf", "zone", "class", "animation", "reveal_steps", "frame_first_seen", "frame_last_seen", "t_first_seen", "t_last_seen")})
    audio = docs.get("audio") or {}
    if audio.get("status") == "ok":
        for k, v in (audio.get("loudness") or {}).items():
            if isinstance(v, (int, float)):
                put(f"audio:loudness:{k}", "audio.json", f"loudness.{k}", v)
        for k in ("onset_count", "share_of_cuts_on_onset", "silence_count", "cuts_within_40ms_of_onset"):
            if k in audio:
                put(f"audio:{k}", "audio.json", k, audio[k])
        tr = audio.get("transcript") or {}
        put("audio:transcript", "audio.json", "transcript", {"status": tr.get("status"), "language": tr.get("language"), "word_count": tr.get("word_count"), "words_per_minute": tr.get("words_per_minute"), "text": (tr.get("text") or "")[:400]})
    elif audio:
        put("audio:status", "audio.json", "status", audio.get("status"))
    sheets = docs.get("sheets") or {}
    for page in (sheets.get("timeline") or {}).get("pages", []):
        put(f"sheet:{page}", "sheets.json", f"timeline.pages[{page}]", {"path": f"sheets/{page}"}, kind="image")
    for page in (sheets.get("shots") or {}).get("pages", []):
        put(f"sheet:{page}", "sheets.json", f"shots.pages[{page}]", {"path": f"sheets/{page}"}, kind="image")
    for k in ("palette_strip", "curves"):
        if sheets.get(k):
            put(f"sheet:{sheets[k]}", "sheets.json", k, {"path": f"sheets/{sheets[k]}"}, kind="image")
    cov = docs.get("coverage") or {}
    if cov:
        put("coverage", "coverage.json", "", {k: cov.get(k) for k in ("decode", "measurement", "model_exposure", "expected_frames", "decoded_frames", "measured_frames")})
    return idx


def write_index(ref_dir: Path, idx: dict[str, dict[str, Any]]) -> Path:
    out = ref_dir / "evidence.json"
    out.write_text(json.dumps({"schema_version": "1.0.0", "method_version": EVIDENCE_VERSION, "count": len(idx), "evidence": idx}, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# ------------------------------------------------------------------------------------- code claims
def _term(dim: str, term: str | None) -> str | None:
    if not term or term == "unclear":
        return None
    return f"{dim}={term}" if registry.resolve(f"{dim}={term}") else None


def _shot_span(s: dict[str, Any]) -> tuple[dict[str, float], dict[str, int]]:
    return ({"start_seconds": float(s["t_in"]), "end_seconds": float(s["t_out"])},
            {"first": int(s["frame_first"]), "last_inclusive": int(s["frame_last_inclusive"])})


def code_claims(asset_id: str, docs: dict[str, Any], idx: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Estimated claims from the measurement stages. Only terms that resolve in the registry are emitted."""
    vocab = registry.vocabulary_version()
    shots = {s["shot_id"]: s for s in (docs.get("shots") or {}).get("shots", [])}
    out: list[dict[str, Any]] = []

    def claim(dim: str, term: str, unit: str, kind: str, span, frames, evidence: list[str], method: str,
              alternatives: list[str] | None = None, limitations: list[str] | None = None, unit_id: str | None = None) -> None:
        tid = _term(dim, term)
        ev = [e for e in evidence if e in idx]
        if not tid or not ev:
            return
        out.append({
            "claim_key": f"{asset_id}|{unit}|{unit_id or '-'}|{dim}|{term}|code",
            "asset_id": asset_id, "vocabulary_version": vocab, "term_id": tid, "dimension": dim, "claim_kind": kind,
            "temporal_unit": unit, "unit_id": unit_id, "time_span": span, "frame_range": frames, "region": None,
            "evidence_ids": ev, "alternatives": [a for a in (alternatives or []) if registry.resolve(f"{dim}={a}")],
            "source": "code", "judges": None, "single_judge": False, "disagreement_group": None,
            "review_status": "pending", "corrected_term_id": None, "method_version": method, "limitations": limitations or [],
        })

    motion = docs.get("motion") or {}
    for m in motion.get("shots", []):
        s = shots.get(m["shot_id"])
        if not s or m.get("status") != "ok" or m.get("class") in (None, "unclear"):
            continue
        span, frames = _shot_span(s)
        claim("camera.movement", m["class"], "shot", "estimated", span, frames,
              [f"motion:{s['shot_id']}:flow_magnitude_pct_w_per_s", f"motion:{s['shot_id']}:flow_divergence_pct_w_per_s",
               f"motion:{s['shot_id']}:flow_jitter_pct_w_per_s", f"shot:{s['shot_id']}"],
              motion.get("method_version", "motion"), alternatives=m.get("alternatives"),
              limitations=["Phase-correlation estimator; mechanism not resolved without parallax evidence"] if str(m["class"]).startswith("apparent_") else [],
              unit_id=s["shot_id"])

    color = docs.get("color") or {}
    for c in color.get("shots", []):
        s = shots.get(c["shot_id"])
        light = c.get("light") or {}
        if not s or c.get("status") != "ok" or not light:
            continue
        span, frames = _shot_span(s)
        sid = s["shot_id"]
        claim("light.key", light.get("key"), "shot", "estimated", span, frames, [f"light:{sid}:key", f"light:{sid}:L_median"], color.get("method_version", "regions"), unit_id=sid)
        claim("light.side", light.get("side"), "shot", "estimated", span, frames, [f"light:{sid}:side", f"light:{sid}:luma_asymmetry"], color.get("method_version", "regions"),
              limitations=["Luma asymmetry of the subject region; ambiguous for flat or symmetric lighting"], unit_id=sid)
        claim("light.quality", light.get("edge"), "shot", "estimated", span, frames, [f"light:{sid}:edge", f"light:{sid}:edge_gradient_p90_median"], color.get("method_version", "regions"),
              limitations=["Edge-gradient proxy at keyframe resolution"], unit_id=sid)

    video_span = None
    if shots:
        first, last = list(shots.values())[0], list(shots.values())[-1]
        video_span = ({"start_seconds": float(first["t_in"]), "end_seconds": float(last["t_out"])},
                      {"first": int(first["frame_first"]), "last_inclusive": int(last["frame_last_inclusive"])})
    montage = (docs.get("shots") or {}).get("montage") or {}
    if video_span and montage:
        cps = (montage.get("cuts_per_s") or {}).get("overall")
        if montage.get("cut_count", 0) == 0:
            pacing = "single_continuous_shot"
        elif cps is not None:
            pacing = "calm_pacing" if cps < 0.3 else ("dynamic_pacing" if cps < 0.8 else "chaotic_pacing")
        else:
            pacing = None
        if pacing:
            claim("montage.pacing", pacing, "video", "estimated", *video_span, ["montage:cuts_per_s", "montage:shot_length_s", "montage:cut_count"],
                  (docs.get("shots") or {}).get("method_version", "shots"), limitations=["Thresholds 0.3 and 0.8 cuts/s are pilot starting values"])

    tracks = (docs.get("text") or {}).get("tracks", [])
    captions = [t for t in tracks if t.get("class") == "subtitle_candidate" or t.get("zone") != "upper_third"]
    if video_span and len(captions) >= 3:
        words = sorted(len((t.get("text") or "").split()) for t in captions)
        median = words[len(words) // 2]
        cadence = "single_word_cues" if median <= 1 else ("phrase_cues" if median <= 4 else "sentence_cues")
        claim("caption.cadence", cadence, "video", "estimated", *video_span, [f"text:{t['track_id']}" for t in captions[:6]],
              (docs.get("text") or {}).get("method_version", "textocr"), limitations=["Median words per caption track; recogniser may merge words"])
    return out
