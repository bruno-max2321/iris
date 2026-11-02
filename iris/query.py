"""`iris query` and `iris observations`.

query: claims across every reference, filtered by term, dimension, review status, source and asset, with
an optional full-text search over caption blocks, transcripts and judge observations. A text search
alone returns the text hits; combined with claim filters it keeps the claims of references that have a hit.

observations: the free-text notes judges leave when the vocabulary cannot say something. A phrase of two
or three words that recurs in at least MIN_REFS different references (a single word: MIN_REFS_ONE_WORD,
since lone words like "small" or "against" recur by chance), and is not already a term or alias of that
dimension, becomes a term proposal for the next minor vocabulary version. Proposals are written to
proposals/term_proposals.json for a person to read; the vocabulary itself is never edited here."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import paths, registry
from .store import Store

MIN_REFS = 3
MIN_REFS_ONE_WORD = 5
MAX_NGRAM = 3
STOPWORDS = frozenset("""a an the and or but of in on at to for from with without by as is are was were be been being it its this that
these those there here very more most less some any each every both all no not only also just than then so such into onto over under
up down out off about across through while when where which who whom what how one two three shot shots frame frames scene video clip
image seems looks appears like feel feels slightly mostly mainly almost quite rather against behind beside near between toward
towards around along within inside outside beneath above below""".split())


def _effective(c: dict[str, Any]) -> str:
    return c["corrected_term_id"] if c.get("review_status") == "corrected" and c.get("corrected_term_id") else c["term_id"]


def _term_matches(c: dict[str, Any], term: str) -> bool:
    """`term` may be dimension=term, a qualified dimension.term id, or a bare term id."""
    eff = _effective(c)
    ref = registry.resolve(term) or registry.resolve(term.replace("=", ".", 1) if "=" in term else term)
    return eff == term or eff.split("=", 1)[1] == term or (ref is not None and eff == f"{ref.dimension}={ref.term}")


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", s.lower())


def _fts_match(text: str, words: list[str]) -> bool:
    have = set(_words(text))
    return all(w in have for w in words)


def _text_hits(asset_ids: list[str], words: list[str], ws: Path) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for aid in asset_ids:
        ref = ws / "refs" / aid
        tp = ref / "text.json"
        if tp.exists():
            text = json.loads(tp.read_text(encoding="utf-8"))
            for b in text.get("blocks") or []:
                if _fts_match(b.get("text") or "", words):
                    hits.append({"asset_id": aid, "kind": "caption", "text": b.get("text"), "frame_first_seen": b.get("frame_first_seen"),
                                 "frame_last_seen": b.get("frame_last_seen"), "track_ids": b.get("track_ids"),
                                 "evidence_ids": [f"text:{t}" for t in b.get("track_ids") or []]})
        ap = ref / "audio.json"
        if ap.exists():
            tr = (json.loads(ap.read_text(encoding="utf-8")).get("transcript") or {})
            ws_ = tr.get("words") or []
            norm = [(_words(w.get("w") or "") or [""])[0] for w in ws_]
            n = len(words)
            for i in range(len(norm) - n + 1):
                if norm[i:i + n] == words:
                    a, b = max(0, i - 6), min(len(ws_), i + n + 6)
                    hits.append({"asset_id": aid, "kind": "transcript", "text": " ".join(w["w"] for w in ws_[a:b]),
                                 "start_seconds": ws_[i]["start"], "end_seconds": ws_[i + n - 1]["end"], "evidence_ids": ["audio:transcript"]})
            if not norm and tr.get("text") and _fts_match(tr["text"], words):
                hits.append({"asset_id": aid, "kind": "transcript", "text": tr["text"][:200], "evidence_ids": ["audio:transcript"]})
        for o in load_observations(ws, [aid]):
            if _fts_match(o["observation"], words):
                hits.append({"asset_id": aid, "kind": "observation", "judge": o["judge"], "unit_id": o.get("unit_id"),
                             "dimension": o["dimension"], "text": o["observation"]})
    return hits


def _assets(ws: Path) -> list[str]:
    return sorted(p.parent.name for p in (ws / "refs").glob("*/manifest.json"))


def query(term: str | None = None, dimension: str | None = None, status: str | None = None, source: str | None = None,
          asset_id: str | None = None, fts: str | None = None, limit: int = 200, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or paths.workspace_root()
    store = Store(ws)
    try:
        rows = store.list_claims(asset_id)
    finally:
        store.close()
    filtered = term or dimension or status or source
    out = []
    for c in rows:
        eff = _effective(c)
        if term and not _term_matches(c, term):
            continue
        if dimension and eff.split("=", 1)[0] != dimension:
            continue
        if status and c["review_status"] != status:
            continue
        if source and c["source"] != source:
            continue
        out.append(c)
    hits: list[dict[str, Any]] = []
    if fts:
        words = _words(fts)
        if not words:
            raise ValueError("--fts needs at least one word")
        scope = sorted({c["asset_id"] for c in out}) if filtered else ([asset_id] if asset_id else _assets(ws))
        hits = _text_hits(scope, words, ws)
        with_hit = {h["asset_id"] for h in hits}
        out = [c for c in out if c["asset_id"] in with_hit] if filtered else []
    compact = [{"claim_id": c["claim_id"], "asset_id": c["asset_id"], "term": _effective(c), "review_status": c["review_status"],
                "source": c["source"], "claim_kind": c["claim_kind"], "unit_id": c.get("unit_id"), "time_span": c.get("time_span"),
                "evidence_ids": c.get("evidence_ids") or []} for c in out]
    by_asset: dict[str, int] = {}
    for c in compact:
        by_asset[c["asset_id"]] = by_asset.get(c["asset_id"], 0) + 1
    return {"ok": True, "filters": {k: v for k, v in {"term": term, "dimension": dimension, "review_status": status, "source": source,
                                                       "asset_id": asset_id, "fts": fts}.items() if v},
            "claims_total": len(compact), "by_asset": by_asset, "claims": compact[:limit], "truncated": len(compact) > limit,
            "text_hits": hits[:limit]}


# ------------------------------------------------------------------------------------- observations
def load_observations(ws: Path, asset_ids: list[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for aid in asset_ids if asset_ids is not None else _assets(ws):
        p = ws / "refs" / aid / "interpret" / "observations.jsonl"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("observation") and o.get("dimension"):
                out.append(o)
    return out


def _phrases(text: str) -> set[str]:
    toks = [w for w in _words(text) if len(w) > 2 and not w.isdigit()]
    out: set[str] = set()
    run: list[str] = []
    for w in toks + [""]:  # n-grams never cross a stopword
        if w and w not in STOPWORDS:
            run.append(w)
            continue
        for n in range(1, MAX_NGRAM + 1):
            for i in range(len(run) - n + 1):
                out.add(" ".join(run[i:i + n]))
        run = []
    return out


def _known(dimension: str) -> set[str]:
    for d in registry.load_vocabulary()["dimensions"]:
        if d["id"] == dimension:
            names = set()
            for t in d["terms"]:
                names.add(t["id"].replace("_", " ").lower())
                names.update(str(a).replace("_", " ").lower() for a in t.get("aliases") or [])
            return names
    return set()


def _next_minor(version: str) -> str:
    parts = (version.split(".") + ["0", "0"])[:3]
    return f"{parts[0]}.{int(parts[1]) + 1}.0" if parts[1].isdigit() else version


def term_proposals(min_refs: int = MIN_REFS, write: bool = True, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or paths.workspace_root()
    obs = load_observations(ws)
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for o in obs:
        for ph in _phrases(o["observation"]):
            g = seen.setdefault((o["dimension"], ph), {"refs": set(), "judges": set(), "examples": []})
            g["refs"].add(o["asset_id"])
            g["judges"].add(o["judge"])
            if len(g["examples"]) < 5 and o["observation"] not in [e["observation"] for e in g["examples"]]:
                g["examples"].append({"asset_id": o["asset_id"], "unit_id": o.get("unit_id"), "judge": o["judge"], "observation": o["observation"]})
    def enough(ph: str, refs: set[str]) -> bool:
        return len(refs) >= (min_refs if " " in ph else max(min_refs, MIN_REFS_ONE_WORD))

    cands = {k: v for k, v in seen.items() if enough(k[1], v["refs"]) and k[1] not in _known(k[0])}
    # keep the longest phrase: drop a phrase contained in a longer candidate seen in the same references
    keep = []
    for (dim, ph), g in cands.items():
        if any(d == dim and p != ph and f" {ph} " in f" {p} " and gg["refs"] >= g["refs"] for (d, p), gg in cands.items()):
            continue
        keep.append({"dimension": dim, "phrase": ph, "suggested_id": ph.replace(" ", "_"), "references": sorted(g["refs"]),
                     "n_refs": len(g["refs"]), "judges": sorted(g["judges"]), "examples": g["examples"]})
    keep.sort(key=lambda x: (-x["n_refs"], x["dimension"], x["phrase"]))
    version = registry.vocabulary_version()
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "vocabulary_version": version,
           "proposed_for": _next_minor(version), "min_refs": min_refs, "min_refs_one_word": max(min_refs, MIN_REFS_ONE_WORD), "observations": len(obs),
           "references_with_observations": len({o["asset_id"] for o in obs}), "proposals": keep,
           "note": "proposals only: a person decides, writes the term card (definition, cues, counterexamples) and bumps the vocabulary"}
    if write:
        p = ws / "proposals" / "term_proposals.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
        doc["path"] = str(p)
    by_dim: dict[str, int] = {}
    for o in obs:
        by_dim[o["dimension"]] = by_dim.get(o["dimension"], 0) + 1
    return {"ok": True, **doc, "by_dimension": by_dim}
