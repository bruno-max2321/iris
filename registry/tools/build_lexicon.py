#!/usr/bin/env python3
"""Generate lexicon.md (one card per term, grouped by dimension) from vocabulary.yaml and bindings/.

Usage:
    python3 tools/build_lexicon.py [--root DIR]          # writes <root>/lexicon.md
    python3 tools/build_lexicon.py --term dolly_in       # prints one card to stdout (backs `iris lexicon <id>`)

Targets Python 3.11 (also runs on 3.9+). Dependency: pyyaml.
Each card starts with an HTML anchor `<a id="<term_id>"></a>` and ends before the next `---` rule,
so a card can be extracted by id without parsing Markdown.
lexicon.md is generated: edit vocabulary.yaml or bindings/*.yaml and re-run this script instead.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import yaml


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def binding_index(root: str) -> dict:
    """term_id -> list of (target, relation, short target description)."""
    idx: dict = {}
    for path in sorted(glob.glob(os.path.join(root, "bindings", "*.yaml"))):
        data = load(path)
        target = data.get("target", os.path.basename(path))
        for r in data.get("rows", []):
            tg = r.get("target") or {}
            if "preset_label" in r:
                desc = f"preset '{r['preset_label']}'"
                ids = [r.get("term_id")] + list(r.get("also_terms", []) or [])
            else:
                ids = [r.get("term_id")]
                if r.get("relation") == "prompt_only":
                    desc = "prompt text"
                elif "param" in tg:
                    v = tg.get("value")
                    desc = f"{tg['param']}={v if v is not None else '<' + str(tg.get('value_hint')) + '>'}"
                elif "command" in tg:
                    p = tg.get("params") or {}
                    desc = tg.get("engine_command") or (f"{tg['command']} {p.get('effect', '')}".strip())
                    if tg["command"] == "add_keyframe":
                        desc = f"add_keyframe {p.get('path')} {p.get('interpolation')}"
                elif "params" in tg or "media_roles" in tg:
                    parts = [f"{k}={v}" for k, v in (tg.get("params") or {}).items()]
                    parts += [f"media:{m}" for m in tg.get("media_roles", []) or []]
                    desc = ", ".join(parts)
                elif "filter" in tg:
                    desc = ",".join(tg.get("filters_used", [])) or tg["filter"][:40]
                else:
                    desc = ""
                if r.get("model"):
                    desc = f"{r['model']}: {desc}"
            for i, tid in enumerate(ids):
                if not tid:
                    continue
                rel = r.get("relation") if i == 0 else "also"
                idx.setdefault(tid, []).append((target, rel, desc))
    return idx


def card(t: dict, dim: dict, binds: list) -> str:
    L = [f'<a id="{t["id"]}"></a>', f"### {t['id']}", ""]
    meta = [f"dimension `{dim['id']}`", f"unit `{dim['temporal_unit']}`", f"claim `{t['claim_kind_default']}`",
            "verified" if t.get("verified") else "**unverified**"]
    if t.get("iris_technique_id"):
        meta.append(f"Iris technique `{t['iris_technique_id']}`")
    if t.get("region_scope"):
        meta.append("regions " + ", ".join(f"`{r}`" for r in t["region_scope"]))
    L.append(" | ".join(meta))
    L.append("")
    L.append(t["definition"])
    L.append("")
    if t.get("aliases"):
        L.append("**Aliases:** " + "; ".join(t["aliases"]))
        L.append("")
    L.append("**Observable cues**")
    L += [f"- {c}" for c in t["observable_cues"]]
    L.append("")
    L.append("**Measurement hints**")
    L += [f"- {h}" for h in t["measurement_hints"]]
    L.append("")
    L.append("**Not to be confused with**")
    for c in t["counterexamples"]:
        who = f"[`{c['confused_with']}`](#{c['confused_with']}): " if c.get("confused_with") else ""
        L.append(f"- {who}{c['distinguish']}")
    L.append("")
    if t.get("related_terms"):
        L.append("**Related:** " + "; ".join(f"{r['relation']} [`{r['term_id']}`](#{r['term_id']})" for r in t["related_terms"]))
        L.append("")
    if t.get("prompt_en"):
        L.append(f"**Prompt phrase:** \"{t['prompt_en']}\"")
        L.append("")
    controls = [b for b in binds if b[1] != "prompt_only"]
    prompt_targets = [b[0] for b in binds if b[1] == "prompt_only"]
    if controls or prompt_targets:
        L.append("**Bindings**")
        L += [f"- {tg}: {rel} - {desc}" for tg, rel, desc in controls]
        if prompt_targets:
            L.append(f"- prompt only on: {', '.join(prompt_targets)}")
        L.append("")
    if t.get("verification_note"):
        L.append(f"**Verification note:** {t['verification_note']}")
        L.append("")
    if t.get("dictionary_ids"):
        L.append("**Dictionary:** " + ", ".join(t["dictionary_ids"]))
        L.append("")
    if t.get("sources"):
        L.append("**Sources**")
        L += [f"- [{s['title']}]({s['url']}) (accessed {s['accessed']})" for s in t["sources"]]
        L.append("")
    L.append("---")
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Generate lexicon.md from vocabulary.yaml")
    ap.add_argument("--root", default=os.path.dirname(here))
    ap.add_argument("--term", help="print the card for one term id (or dimension=term) and exit")
    args = ap.parse_args(argv)
    vocab = load(os.path.join(args.root, "vocabulary.yaml"))
    binds = binding_index(args.root)

    if args.term:
        want = args.term.split("=")[-1]
        for d in vocab["dimensions"]:
            for t in d["terms"]:
                if t["id"] == want or want in [a.lower() for a in t.get("aliases", [])]:
                    print(card(t, d, binds.get(t["id"], [])))
                    return 0
        print(f"unknown term: {args.term}", file=sys.stderr)
        return 1

    n = sum(len(d["terms"]) for d in vocab["dimensions"])
    out = [
        "# Iris lexicon",
        "",
        f"Generated from `vocabulary.yaml` v{vocab['version']} ({vocab['generated_at']}) by `tools/build_lexicon.py`. Do not edit by hand.",
        f"{len(vocab['dimensions'])} dimensions, {n} terms. Look up one card with `iris lexicon <term_id>` "
        "or `python3 tools/build_lexicon.py --term <term_id>`.",
        "",
        "## Dimensions",
        "",
    ]
    for d in vocab["dimensions"]:
        out.append(f"- [{d['id']}](#dim-{d['id'].replace('.', '-')}) ({d['temporal_unit']}, {d['cardinality']}, {len(d['terms'])} terms)")
    out.append("")
    for d in vocab["dimensions"]:
        out.append(f'<a id="dim-{d["id"].replace(".", "-")}"></a>')
        out.append(f"## {d['id']}")
        out.append("")
        out.append(f"Temporal unit `{d['temporal_unit']}`, cardinality `{d['cardinality']}`"
                   + (", region-scoped" if d.get("region_scoped") else "") + ".")
        out.append("")
        out.append(d["description"])
        out.append("")
        if d.get("qualifiers"):
            for q in d["qualifiers"]:
                scope = f" (applies to {', '.join(q['applies_to'])})" if q.get("applies_to") else ""
                out.append(f"- Qualifier `{q['id']}`: {', '.join(q['values'])}{scope}. {q['description']}")
            out.append("")
        if d.get("exclusive_groups"):
            for g in d["exclusive_groups"]:
                out.append(f"- Mutually exclusive: {', '.join(g)}")
            out.append("")
        out.append("Measurement keys: " + ", ".join(f"`{k}`" for k in d["measurement_keys"]))
        out.append("")
        for t in d["terms"]:
            out.append(card(t, d, binds.get(t["id"], [])))
    path = os.path.join(args.root, "lexicon.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    print(f"wrote {path}: {len(vocab['dimensions'])} dimensions, {n} cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
