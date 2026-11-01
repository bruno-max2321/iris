#!/usr/bin/env python3
"""Validate the Iris creative vocabulary and its binding tables.

Usage:
    python3 tools/validate_vocabulary.py [--root DIR] [--catalog FILE] [--strict] [--quiet]

Targets Python 3.11 (also runs on 3.9+). Dependencies: pyyaml, jsonschema.

Checks:
  1. vocabulary.yaml is valid against vocabulary.schema.json (JSON Schema 2020-12).
  2. Dimension ids and term ids are unique (term ids are unique across all dimensions).
  3. Internal references resolve: counterexamples.confused_with, related_terms, exclusive_groups,
     qualifiers.applies_to, and every dimension measurement key is declared in measurement_keys.
  4. iris_technique_id is one of the 43 Iris technique ids, and each of the 43 appears exactly once.
  5. Terms in region-scoped dimensions declare region_scope; others do not.
  6. Verified camera, light and optics terms cite at least one official Higgsfield source (higgsfield.ai);
     unverified ones without such a source are reported as warnings.
  7. The term count is within 180-320 and no Spanish-only fields or characters are present.
  8. Every binding row references an existing term_id and a valid relation; prompt_only rows carry a prompt.
  9. Higgsfield bindings use only model ids, parameters, enum values and media roles present in the
     MCP catalog snapshot. A null value is allowed only for a non-enum parameter and must carry a
     value_hint (reported as unresolved).
 10. The Camera Controls table has exactly the 65 public preset labels of dictionary category 20.
 11. EffectCraft rows use MCP tools, parameters, enums, engine commands, effects and effect parameters
     present in the capabilities extract.
 12. FFmpeg rows use filters, xfade transitions and curves presets present in the capabilities capture
     (filters listed in build_requires are reported as warnings).
 13. Dictionary vocab_term_id links point to existing terms, and term dictionary_ids exist.

Exit code 0 when there are no errors (warnings allowed unless --strict), 1 otherwise.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

import jsonschema
import yaml

IRIS_43 = [
    "chiaroscuro", "rimlight", "complementary", "simultaneous", "warmcool", "satblock", "silhouette", "dof",
    "texture", "facture", "isolation", "popout", "scaledisparity", "caricature", "juxtaposition", "patternbreak",
    "proximity", "similarity", "commonregion", "continuity", "symmetry", "figureground", "closure", "compounding",
    "leadinglines", "gaze", "vector", "hierarchy", "readingpath", "centralbias", "framewithin", "crop", "occlusion",
    "forcedperspective", "temporalsynthesis", "pareidolia", "personification", "displacement", "substitution",
    "contextual", "inscenetext", "genre", "genrequotation",
]
RELATIONS = {"exact", "approx", "prompt_only", "unsupported"}
OFFICIAL_DIM_PREFIXES = ("camera.", "light.", "optics")
TERM_MIN, TERM_MAX = 180, 320
SPANISH_MARKERS = re.compile("[\u00f1\u00d1\u00bf\u00a1]")  # n-tilde, inverted ? and !
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load_yaml(path: str):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def walk_strings(obj, path=""):
    """Yield (path, key_or_None, string) for every string and key in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, None
            yield from walk_strings(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, None, obj


def check_language(obj, label: str, rep: Report) -> None:
    for path, key, text in walk_strings(obj):
        if key is not None and (key.endswith("_es") or key.startswith("es_")):
            rep.err(f"{label}: Spanish-only field '{key}' at {path or '/'}")
        if text is not None and SPANISH_MARKERS.search(text):
            rep.err(f"{label}: Spanish character in {path}: {text[:60]!r}")


# --------------------------------------------------------------------------- vocabulary
def check_vocabulary(root: str, rep: Report):
    vocab = load_yaml(os.path.join(root, "vocabulary.yaml"))
    schema = load_json(os.path.join(root, "vocabulary.schema.json"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    for e in sorted(validator.iter_errors(vocab), key=lambda x: list(x.absolute_path)):
        rep.err("schema: /" + "/".join(str(p) for p in e.absolute_path) + ": " + e.message[:200])

    terms: dict[str, dict] = {}
    dim_of: dict[str, str] = {}
    dim_ids: set[str] = set()
    for d in vocab.get("dimensions", []):
        if d["id"] in dim_ids:
            rep.err(f"duplicate dimension id {d['id']}")
        dim_ids.add(d["id"])
        for t in d.get("terms", []):
            if t["id"] in terms:
                rep.err(f"duplicate term id {t['id']} (in {dim_of[t['id']]} and {d['id']})")
            terms[t["id"]] = t
            dim_of[t["id"]] = d["id"]
    clash = dim_ids & set(terms)
    if clash:
        rep.err(f"ids used both as dimension and term: {sorted(clash)}")

    declared_keys = set(vocab.get("measurement_keys", {}))
    used_keys: set[str] = set()
    iris_seen: collections.Counter = collections.Counter()
    if vocab.get("iris_techniques") != IRIS_43:
        rep.err("header iris_techniques differs from the 43 Iris technique ids")

    for d in vocab.get("dimensions", []):
        dterm_ids = {t["id"] for t in d["terms"]}
        for k in d.get("measurement_keys", []):
            used_keys.add(k)
            if k not in declared_keys:
                rep.err(f"{d['id']}: measurement key {k} not declared in measurement_keys")
        for q in d.get("qualifiers", []) or []:
            for tid in q.get("applies_to", []) or []:
                if tid not in dterm_ids:
                    rep.err(f"{d['id']}: qualifier {q['id']} applies_to unknown term {tid}")
        for g in d.get("exclusive_groups", []) or []:
            for tid in g:
                if tid not in dterm_ids:
                    rep.err(f"{d['id']}: exclusive group member {tid} is not a term of this dimension")
        if d.get("cardinality") == "single" and d.get("exclusive_groups"):
            rep.warn(f"{d['id']}: exclusive_groups on a single-cardinality dimension is redundant")
        for t in d["terms"]:
            tid = t["id"]
            for c in t.get("counterexamples", []):
                cw = c.get("confused_with")
                if cw is not None:
                    if cw not in terms:
                        rep.err(f"{tid}: counterexample confused_with unknown term {cw}")
                    elif cw == tid:
                        rep.err(f"{tid}: counterexample points to itself")
            for r in t.get("related_terms", []) or []:
                if r["term_id"] not in terms:
                    rep.err(f"{tid}: related term {r['term_id']} does not exist")
            iid = t.get("iris_technique_id")
            if iid is not None:
                if iid not in IRIS_43:
                    rep.err(f"{tid}: iris_technique_id {iid} is not one of the 43 Iris techniques")
                iris_seen[iid] += 1
            if d.get("region_scoped") and not t.get("region_scope"):
                rep.err(f"{tid}: dimension {d['id']} is region-scoped but the term has no region_scope")
            if not d.get("region_scoped") and t.get("region_scope"):
                rep.warn(f"{tid}: region_scope on a non-region-scoped dimension")
            if d["id"].startswith(OFFICIAL_DIM_PREFIXES):
                if not any("higgsfield.ai" in s["url"] for s in t.get("sources", [])):
                    if t.get("verified"):
                        rep.err(f"{tid}: verified camera/light/optics term without an official Higgsfield source")
                    else:
                        rep.warn(f"{tid}: camera/light/optics term without a Higgsfield source (marked verified: false)")
            if not t.get("verified") and not t.get("verification_note"):
                rep.err(f"{tid}: verified false without verification_note")
    for iid in IRIS_43:
        if iris_seen[iid] != 1:
            rep.err(f"iris technique {iid} mapped by {iris_seen[iid]} terms (expected exactly 1)")
    unused = declared_keys - used_keys
    if unused:
        rep.warn(f"{len(unused)} declared measurement keys are not used by any dimension: {sorted(unused)[:8]}")
    if not TERM_MIN <= len(terms) <= TERM_MAX:
        rep.err(f"term count {len(terms)} outside {TERM_MIN}-{TERM_MAX}")
    if vocab.get("language") != "en":
        rep.err("header language must be 'en'")
    check_language(vocab, "vocabulary.yaml", rep)
    return vocab, terms, dim_of


# --------------------------------------------------------------------------- bindings
def common_row_checks(fname: str, i: int, row: dict, terms: dict, rep: Report, allow_null_term=False) -> bool:
    where = f"{fname} row {i}"
    tid = row.get("term_id")
    ok = True
    if tid is None:
        if not allow_null_term:
            rep.err(f"{where}: term_id missing")
            ok = False
    elif tid not in terms:
        rep.err(f"{where}: unknown term_id {tid}")
        ok = False
    if row.get("relation") not in RELATIONS:
        rep.err(f"{where}: invalid relation {row.get('relation')!r}")
        ok = False
    vo = row.get("verified_on")
    if not isinstance(vo, str) or not DATE_RE.match(vo):
        rep.err(f"{where}: verified_on must be an ISO date")
    if "notes" not in row:
        rep.err(f"{where}: notes missing")
    return ok


def catalog_index(catalog: dict) -> dict:
    idx = {}
    for it in catalog["items"]:
        params = {p["name"]: p for p in it.get("parameters", [])}
        roles = {r for m in it.get("medias", []) or [] for r in m.get("roles", [])}
        idx[it["id"]] = {"params": params, "roles": roles}
    return idx


def check_hf_value(where: str, model: str, pname: str, value, hint, cat: dict, rep: Report, stats: dict) -> None:
    m = cat.get(model)
    if m is None:
        rep.err(f"{where}: model {model} not in MCP catalog")
        return
    p = m["params"].get(pname)
    if p is None:
        rep.err(f"{where}: parameter {pname} not exposed by {model}")
        return
    opts = p.get("options")
    if value is None:
        if opts:
            rep.err(f"{where}: {model}.{pname} is an enum; a null value is not allowed")
        elif not hint:
            rep.err(f"{where}: null value for {model}.{pname} without value_hint")
        else:
            stats["unresolved"] += 1
        return
    if opts is not None and value not in opts:
        rep.err(f"{where}: value {value!r} not in {model}.{pname} options {opts}")
    if p.get("type") == "bool" and not isinstance(value, bool):
        rep.err(f"{where}: {model}.{pname} expects a boolean")


def check_higgsfield_binding(fname: str, data: dict, terms: dict, cat: dict, rep: Report, stats: dict) -> None:
    file_model = data.get("model_id")
    if file_model not in cat:
        rep.err(f"{fname}: model_id {file_model} not in MCP catalog")
    for kind, enums in (data.get("unbound_enums") or {}).items():
        p = cat.get(file_model, {}).get("params", {}).get(kind)
        if p is None:
            rep.err(f"{fname}: unbound_enums parameter {kind} not in {file_model}")
            continue
        for v in enums:
            if v not in (p.get("options") or []):
                rep.err(f"{fname}: unbound enum value {v} not in {file_model}.{kind}")
    for i, row in enumerate(data.get("rows", [])):
        where = f"{fname} row {i} ({row.get('term_id')})"
        if not common_row_checks(fname, i, row, terms, rep):
            continue
        model = row.get("model", file_model)
        tg = row.get("target") or {}
        hint = tg.get("value_hint")
        if row["relation"] == "prompt_only":
            if not tg.get("prompt"):
                rep.err(f"{where}: prompt_only row without target.prompt")
            if set(tg) - {"prompt"}:
                rep.err(f"{where}: prompt_only row must not set parameters")
            continue
        if row["relation"] == "unsupported":
            continue
        touched = False
        if "param" in tg:
            check_hf_value(where, model, tg["param"], tg.get("value"), hint, cat, rep, stats)
            touched = True
        for pname, val in (tg.get("params") or {}).items():
            check_hf_value(where, model, pname, val, hint, cat, rep, stats)
            touched = True
        for role in tg.get("media_roles", []) or []:
            if role not in cat.get(model, {}).get("roles", set()):
                rep.err(f"{where}: media role {role} not accepted by {model}")
            touched = True
        if not touched:
            rep.err(f"{where}: {row['relation']} row sets no parameter or media role")
        unknown = set(tg) - {"param", "value", "params", "value_hint", "media_roles", "prompt"}
        if unknown:
            rep.err(f"{where}: unknown target keys {sorted(unknown)}")


def check_camera_controls(fname: str, data: dict, terms: dict, dictionary: dict, rep: Report) -> None:
    rows = data.get("rows", [])
    labels = [r.get("preset_label") for r in rows]
    cat20 = {e["term"]: e for e in dictionary["entries"] if str(e.get("category", "")).startswith("20 ")}
    sources = {x["id"]: x for x in dictionary.get("sources", [])}
    if len(rows) != 65:
        rep.err(f"{fname}: expected 65 presets, found {len(rows)}")
    dup = [l for l, n in collections.Counter(labels).items() if n > 1]
    if dup:
        rep.err(f"{fname}: duplicate preset labels {dup}")
    missing, extra = set(cat20) - set(labels), set(labels) - set(cat20)
    if missing or extra:
        rep.err(f"{fname}: labels differ from dictionary category 20 (missing {sorted(missing)}, extra {sorted(extra)})")
    for i, r in enumerate(rows):
        where = f"{fname} row {i} ({r.get('preset_label')})"
        common_row_checks(fname, i, r, terms, rep, allow_null_term=True)
        if (r.get("term_id") is None) != (r.get("relation") == "unsupported"):
            rep.err(f"{where}: term_id null if and only if relation is unsupported")
        if r.get("relation") == "prompt_only":
            rep.err(f"{where}: prompt_only is not meaningful for a preset")
        for a in r.get("also_terms", []) or []:
            if a not in terms:
                rep.err(f"{where}: also_terms has unknown term {a}")
        e = cat20.get(r.get("preset_label"))
        if e:
            accepted = set(e.get("source_urls", []))
            # Presets whose page failed during the dictionary research keep their intended page as attempted_source_id.
            att = sources.get(e.get("attempted_source_id"))
            if att:
                accepted.add(att["url"])
            if r.get("motion_url") not in accepted:
                rep.err(f"{where}: motion_url does not match the dictionary source")
        if e and e.get("vocab_term_id") != r.get("term_id"):
            rep.warn(f"{where}: dictionary vocab_term_id {e.get('vocab_term_id')} differs from binding term_id {r.get('term_id')}")


def check_effectcraft(fname: str, data: dict, terms: dict, caps: dict, rep: Report) -> None:
    tools, cmds, effects = caps["mcp_tools"], caps["engine_commands"], caps["effects"]
    for i, row in enumerate(data.get("rows", [])):
        where = f"{fname} row {i} ({row.get('term_id')})"
        if not common_row_checks(fname, i, row, terms, rep):
            continue
        tg = row.get("target") or {}
        if row["relation"] in ("prompt_only", "unsupported"):
            continue
        tool = tg.get("command")
        if tool not in tools:
            rep.err(f"{where}: MCP tool {tool!r} not in the EffectCraft extract")
            continue
        params = tg.get("params") or {}
        if tool == "execute_command":
            ec = tg.get("engine_command")
            if ec not in cmds:
                rep.err(f"{where}: engine command {ec!r} not in the extract")
                continue
            allowed = set(cmds[ec])
            if not allowed and params:
                rep.warn(f"{where}: engine command {ec} publishes no parameter schema; params unchecked")
            else:
                bad = set(params) - allowed
                if bad:
                    rep.err(f"{where}: {ec} has no parameter(s) {sorted(bad)}; allowed {sorted(allowed)}")
            continue
        bad = set(params) - set(tools[tool]["params"])
        if bad:
            rep.err(f"{where}: {tool} has no parameter(s) {sorted(bad)}")
        for k, opts in tools[tool].get("enums", {}).items():
            if k in params and params[k] not in opts:
                rep.err(f"{where}: {tool}.{k}={params[k]!r} not in {opts}")
        if tool == "add_effect":
            eff = params.get("effect")
            if eff not in effects:
                rep.err(f"{where}: effect {eff!r} not in the extract")
                continue
            badv = set(params.get("values") or {}) - set(effects[eff])
            if badv:
                rep.err(f"{where}: effect {eff} has no parameter(s) {sorted(badv)}")


XFADE_RE = re.compile(r"transition=([a-z]+)")
CURVES_RE = re.compile(r"curves=preset=([a-z_]+)")


def check_ffmpeg(fname: str, data: dict, terms: dict, caps: dict, rep: Report) -> None:
    filters, trans, presets = set(caps["filters"]), set(caps["xfade_transitions"]), set(caps["curves_presets"])
    if not filters:
        rep.err(f"{fname}: ffmpeg capabilities capture lists no filters")
    for i, row in enumerate(data.get("rows", [])):
        where = f"{fname} row {i} ({row.get('term_id')})"
        if not common_row_checks(fname, i, row, terms, rep):
            continue
        tg = row.get("target") or {}
        if row["relation"] in ("prompt_only", "unsupported"):
            continue
        flt = tg.get("filter")
        if not flt:
            rep.err(f"{where}: missing filter string")
            continue
        req = tg.get("build_requires") or []
        for f in tg.get("filters_used", []):
            if not re.search(r"(^|[\];,])\s*(\[[^\]]*\]\s*)*" + re.escape(f) + r"(=|,|$|\[)", flt):
                rep.err(f"{where}: filters_used lists {f} but the filter string does not use it")
            if f not in filters:
                if req:
                    rep.warn(f"{where}: filter {f} absent from the capture (build requires {', '.join(req)})")
                else:
                    rep.err(f"{where}: filter {f} not in the ffmpeg capture")
        for t in XFADE_RE.findall(flt):
            if t not in trans:
                rep.err(f"{where}: xfade transition {t} not in the capture")
        for p in CURVES_RE.findall(flt):
            if p not in presets:
                rep.err(f"{where}: curves preset {p} not in the capture")


def check_dictionary(dictionary: dict, terms: dict, rep: Report) -> dict:
    ids = set()
    linked = 0
    for e in dictionary["entries"]:
        ids.add(e["id"])
        v = e.get("vocab_term_id")
        vs = e.get("vocab_term_ids", [])
        if "vocab_term_id" not in e:
            rep.err(f"dictionary {e['id']}: vocab_term_id field missing")
        if v is not None:
            linked += 1
            if v not in terms:
                rep.err(f"dictionary {e['id']}: vocab_term_id {v} does not exist")
            if v not in vs:
                rep.err(f"dictionary {e['id']}: vocab_term_id not listed in vocab_term_ids")
        for x in vs:
            if x not in terms:
                rep.err(f"dictionary {e['id']}: vocab_term_ids has unknown term {x}")
    for tid, t in terms.items():
        for did in t.get("dictionary_ids", []) or []:
            if did not in ids:
                rep.err(f"{tid}: dictionary id {did} not in the dictionary")
    return {"entries": len(dictionary["entries"]), "linked": linked}


# --------------------------------------------------------------------------- main
def main(argv=None) -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=os.path.dirname(here), help="vocabulario/ directory")
    ap.add_argument("--catalog", default=None, help="MCP video catalog JSON (default: <root>/capabilities/mcp-higgsfield-video-2026-11-01.json)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--quiet", action="store_true", help="print only the summary and problems")
    args = ap.parse_args(argv)
    root = args.root
    rep = Report()

    vocab, terms, dim_of = check_vocabulary(root, rep)
    catalog = load_json(args.catalog or os.path.join(root, "capabilities", "mcp-higgsfield-video-2026-11-01.json"))
    cat = catalog_index(catalog)
    dictionary = load_json(os.path.join(root, "dictionaries", "higgsfield-codex-2026-11-01.json"))
    dstats = check_dictionary(dictionary, terms, rep)

    per_file = {}
    covered = collections.defaultdict(set)
    stats = {"unresolved": 0}
    for path in sorted(glob.glob(os.path.join(root, "bindings", "*.yaml"))):
        fname = os.path.basename(path)
        data = load_yaml(path)
        check_language(data, fname, rep)
        target = data.get("target", "")
        if fname == "higgsfield-camera-controls.yaml":
            check_camera_controls(fname, data, terms, dictionary, rep)
        elif fname.startswith("higgsfield-"):
            check_higgsfield_binding(fname, data, terms, cat, rep, stats)
        elif fname.startswith("effectcraft"):
            check_effectcraft(fname, data, terms, load_json(os.path.join(root, data["capabilities"])), rep)
        elif fname.startswith("ffmpeg"):
            check_ffmpeg(fname, data, terms, load_json(os.path.join(root, data["capabilities"])), rep)
        else:
            rep.warn(f"{fname}: unknown binding target {target}; only generic row checks applied")
            for i, row in enumerate(data.get("rows", [])):
                common_row_checks(fname, i, row, terms, rep)
        rel = collections.Counter(r.get("relation") for r in data.get("rows", []))
        per_file[fname] = (len(data.get("rows", [])), rel)
        for r in data.get("rows", []):
            if r.get("relation") in ("exact", "approx") and r.get("term_id"):
                covered[r["term_id"]].add(fname)
            for a in r.get("also_terms", []) or []:
                covered[a].add(fname)

    # ---- summary
    dims = vocab.get("dimensions", [])
    print("Iris vocabulary validation")
    print(f"  root: {root}")
    print(f"  version {vocab.get('version')} | language {vocab.get('language')} | {len(dims)} dimensions | {len(terms)} terms | "
          f"{len(vocab.get('measurement_keys', {}))} measurement keys")
    if not args.quiet:
        for d in dims:
            nv = sum(1 for t in d["terms"] if not t.get("verified"))
            print(f"    {d['id']:<26} {d['temporal_unit']:<8} {d['cardinality']:<6} terms={len(d['terms']):<3} unverified={nv}")
    unverified = [t for t in terms.values() if not t.get("verified")]
    print(f"  verified: {len(terms) - len(unverified)} | unverified: {len(unverified)} | iris techniques mapped: "
          f"{sum(1 for t in terms.values() if t.get('iris_technique_id'))}/43")
    print("  bindings (rows: exact/approx/prompt_only/unsupported):")
    for fname, (n, rel) in per_file.items():
        print(f"    {fname:<36} {n:>4}: {rel.get('exact', 0)}/{rel.get('approx', 0)}/{rel.get('prompt_only', 0)}/{rel.get('unsupported', 0)}")
    print(f"  terms with at least one exact/approx binding: {len(covered)}/{len(terms)}")
    print(f"  unresolved Higgsfield ids (value null + value_hint, resolve at runtime): {stats['unresolved']}")
    print(f"  dictionary: {dstats['entries']} entries, {dstats['linked']} linked to a term")
    for w in rep.warnings:
        print(f"  WARNING {w}")
    for e in rep.errors:
        print(f"  ERROR {e}")
    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))
    print(f"RESULT: {'FAIL' if failed else 'OK'} ({len(rep.errors)} errors, {len(rep.warnings)} warnings)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
