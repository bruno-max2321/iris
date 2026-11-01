"""Iris command-line interface.

Contract: structured JSON on stdout, progress on stderr, stable exit codes (iris/exit_codes.py).
Long operations return a job_id immediately once implemented. Commands not yet implemented exit with
code 9 and a JSON payload naming the milestone that delivers them."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

from . import __version__, doctor, exit_codes, paths, registry

MILESTONE = {
    "ingest": 1, "analyze": 2, "interpret": 3, "validate": 3, "claims": 3, "review": 3,
    "style": 4, "check": 4, "jobs": 1, "query": 5, "report": 5, "ledger": 3, "gc": 5,
}


def _emit(payload: dict[str, Any], code: int = exit_codes.OK) -> int:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return code


def _not_implemented(cmd: str) -> int:
    return _emit(exit_codes.error_payload(exit_codes.NOT_IMPLEMENTED, f"'{cmd}' is not implemented yet",
                                          milestone=MILESTONE.get(cmd)), exit_codes.NOT_IMPLEMENTED)


def cmd_version(_: argparse.Namespace) -> int:
    return _emit({"ok": True, "iris": __version__, "vocabulary": registry.vocabulary_version()})


def cmd_doctor(args: argparse.Namespace) -> int:
    if args.install:
        return _emit(exit_codes.error_payload(exit_codes.NOT_IMPLEMENTED, "doctor --install arrives with milestone 0 on the VM"),
                     exit_codes.NOT_IMPLEMENTED)
    result = doctor.run()
    return _emit(result, exit_codes.OK if result["ok"] else exit_codes.VALIDATION)


def cmd_lexicon(args: argparse.Namespace) -> int:
    card = registry.lexicon_card(args.ref)
    if card is None:
        return _emit(exit_codes.error_payload(exit_codes.VALIDATION, f"unknown term or dimension: {args.ref}",
                                              hint="use 'dimension.term', 'dimension=term', a bare Iris composition id, or a dimension id"),
                     exit_codes.VALIDATION)
    return _emit({"ok": True, "vocabulary": registry.vocabulary_version(), **card})


def cmd_selftest(args: argparse.Namespace) -> int:
    """Run the registry validator, the Style Bible example validation and the unit tests."""
    results: dict[str, Any] = {}
    rc_total = exit_codes.OK
    validator = paths.REGISTRY_DIR / "tools" / "validate_vocabulary.py"
    p = subprocess.run([sys.executable, str(validator)], capture_output=True, text=True)
    results["vocabulary_validator"] = {"exit": p.returncode, "tail": p.stdout.strip().splitlines()[-1:] or p.stderr.strip().splitlines()[-1:]}
    if p.returncode != 0:
        rc_total = exit_codes.VALIDATION
    results["schemas"] = doctor.check_schemas()
    if results["schemas"]["status"] != "ok":
        rc_total = exit_codes.VALIDATION
    if not args.no_tests:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", str(paths.REPO_ROOT / "tests")], capture_output=True, text=True)
        results["pytest"] = {"exit": p.returncode, "tail": (p.stdout.strip().splitlines() or [""])[-1]}
        if p.returncode != 0:
            rc_total = exit_codes.VALIDATION
    if args.golden:
        results["golden"] = exit_codes.error_payload(exit_codes.NOT_IMPLEMENTED, "golden reference arrives with milestone 5")
    return _emit({"ok": rc_total == exit_codes.OK, "results": results}, rc_total)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="iris", description="Iris: visual-style analysis with a closed vocabulary.")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("version", help="Print versions").set_defaults(func=cmd_version)

    d = sub.add_parser("doctor", help="Verify the environment")
    d.add_argument("--install", action="store_true", help="Install or repair the environment (VM only)")
    d.set_defaults(func=cmd_doctor)

    lx = sub.add_parser("lexicon", help="Show a term card or a dimension summary")
    lx.add_argument("ref", help="term id (dimension.term, dimension=term, bare Iris id) or dimension id")
    lx.set_defaults(func=cmd_lexicon)

    st = sub.add_parser("selftest", help="Validate registry, schemas and run unit tests")
    st.add_argument("--golden", action="store_true")
    st.add_argument("--no-tests", action="store_true")
    st.set_defaults(func=cmd_selftest)

    for name, helptext in [
        ("ingest", "Register a reference from a URL or file"),
        ("analyze", "Measure a registered asset (stages A–I)"),
        ("interpret", "Prepare, ingest or run closed-vocabulary interpretation"),
        ("validate", "Validate claims and observations"),
        ("claims", "List claims"),
        ("review", "Record human review decisions"),
        ("style", "Build or lint a Style Bible"),
        ("check", "Evaluate a clip against a Style Bible"),
        ("jobs", "Inspect, resume or cancel jobs"),
        ("query", "Search accepted claims and references"),
        ("report", "Export the HTML report"),
        ("ledger", "Summarize agent calls and cost"),
        ("gc", "Apply the retention policy"),
    ]:
        sp = sub.add_parser(name, help=f"{helptext} (milestone {MILESTONE[name]})")
        sp.add_argument("rest", nargs=argparse.REMAINDER)
        sp.set_defaults(func=lambda a, _n=name: _not_implemented(_n))
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
