"""Load the closed vocabulary and answer `iris lexicon` queries.

The vocabulary is the single term registry (registry/vocabulary.yaml). A term reference may be a bare
Iris composition id (e.g. `isolation`) or a qualified `dimension.term` / `dimension=term` id."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

import yaml

from .paths import VOCABULARY_FILE


@dataclass(frozen=True)
class TermRef:
    dimension: str
    term: str

    @property
    def qualified(self) -> str:
        return f"{self.dimension}.{self.term}"


@functools.lru_cache(maxsize=1)
def load_vocabulary() -> dict[str, Any]:
    with VOCABULARY_FILE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def vocabulary_version() -> str:
    return str(load_vocabulary()["version"])


@functools.lru_cache(maxsize=1)
def _index() -> dict[str, tuple[str, dict[str, Any]]]:
    """Map every accepted reference form to (dimension_id, term_dict)."""
    idx: dict[str, tuple[str, dict[str, Any]]] = {}
    for dim in load_vocabulary()["dimensions"]:
        did = dim["id"]
        for term in dim["terms"]:
            tid = term["id"]
            idx[f"{did}.{tid}"] = (did, term)
            idx[f"{did}={tid}"] = (did, term)
            if did == "composition":
                idx[tid] = (did, term)
    return idx


def resolve(ref: str) -> TermRef | None:
    hit = _index().get(ref)
    if hit is None:
        return None
    did, term = hit
    return TermRef(did, term["id"])


def is_valid_ref(ref: str) -> bool:
    return resolve(ref) is not None


def dimension(did: str) -> dict[str, Any] | None:
    for dim in load_vocabulary()["dimensions"]:
        if dim["id"] == did:
            return dim
    return None


def term_ids(did: str) -> list[str]:
    dim = dimension(did)
    return [t["id"] for t in dim["terms"]] if dim else []


def lexicon_card(ref: str) -> dict[str, Any] | None:
    """Return the lexicon card for a term, or a dimension summary when `ref` is a dimension id."""
    hit = _index().get(ref)
    if hit is not None:
        did, term = hit
        dim = dimension(did) or {}
        return {
            "kind": "term",
            "dimension": did,
            "temporal_unit": dim.get("temporal_unit"),
            "region_scoped": dim.get("region_scoped", False),
            **{k: term.get(k) for k in (
                "id", "aliases", "definition", "observable_cues", "measurement_hints",
                "counterexamples", "claim_kind_default", "prompt_en", "related_terms",
                "region_scope", "dictionary_ids", "sources", "verified", "verification_note",
            ) if term.get(k) is not None},
        }
    dim = dimension(ref)
    if dim is not None:
        return {
            "kind": "dimension",
            "id": dim["id"],
            "temporal_unit": dim.get("temporal_unit"),
            "cardinality": dim.get("cardinality"),
            "description": dim.get("description"),
            "measurement_keys": dim.get("measurement_keys", []),
            "terms": [t["id"] for t in dim["terms"]],
            "accepts_unclear": True,
        }
    return None
