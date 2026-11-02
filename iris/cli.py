"""Iris command-line interface.

Contract: structured JSON on stdout, progress on stderr, stable exit codes (iris/exit_codes.py).
Long operations return a job_id immediately once implemented. Commands not yet implemented exit with
code 9 and a JSON payload naming the milestone that delivers them."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

from . import __version__, doctor, exit_codes, paths, registry

MILESTONE = {"query": 5, "report": 5, "gc": 5}

_CODE_BY_NAME = {v: k for k, v in exit_codes.NAMES.items()}


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


def cmd_ingest(args: argparse.Namespace) -> int:
    from . import ingest

    try:
        res = ingest.ingest(args.source, args.rights, copy_local=args.copy)
    except ingest.IngestError as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.INPUT_UNAVAILABLE)
        return _emit(exit_codes.error_payload(code, str(exc)), code)
    m = res["manifest"]
    return _emit({"ok": True, "asset_id": res["asset_id"], "created": res["created"], "readable": m["readable"],
                  "bytes": m["bytes"], "source": m["source"], "probe": m["probe"], "manifest": str(paths.workspace_root() / "refs" / res["asset_id"] / "manifest.json")})


def cmd_analyze(args: argparse.Namespace) -> int:
    from . import analyze, ingest

    try:
        stages = [x.strip() for x in args.stages.split(",") if x.strip()] if args.stages else None
        out = analyze.analyze(args.asset_id, mode=args.mode, force=args.force, stages=stages)
    except (analyze.AnalyzeError, ingest.IngestError) as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.VALIDATION)
        return _emit(exit_codes.error_payload(code, str(exc)), code)
    cov = out.get("coverage") or {}
    code = exit_codes.OK if cov.get("decode") == "full" and cov.get("measurement") == "full" else exit_codes.PARTIAL
    return _emit({"ok": code == exit_codes.OK, "job_id": out["job"]["job_id"], "state": out["job"]["state"],
                  "created": out["created"], "coverage": cov, "index": out.get("index_summary"),
                  "measure": out.get("measure_summary"), "stages": out.get("stages")}, code)


def cmd_jobs(args: argparse.Namespace) -> int:
    from . import analyze
    from .store import Store

    store = Store()
    try:
        if args.action == "list":
            return _emit({"ok": True, "jobs": store.list_jobs(args.asset_id)})
        job = store.get_job(args.job_id) if args.job_id else None
        if job is None:
            return _emit(exit_codes.error_payload(exit_codes.USAGE, f"unknown job {args.job_id}"), exit_codes.USAGE)
        if args.action == "status":
            return _emit({"ok": True, "job": job})
        if args.action == "cancel":
            job = store.update_job(job["job_id"], state="canceled")
            return _emit({"ok": True, "job": job})
    finally:
        store.close()
    # resume: re-run analyze; checkpoints make it skip completed stages
    try:
        out = analyze.analyze(job["asset_id"], mode=job.get("mode") or "economy")
    except analyze.AnalyzeError as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.VALIDATION)
        return _emit(exit_codes.error_payload(code, str(exc)), code)
    return _emit({"ok": True, "job": out["job"], "coverage": out.get("coverage")})


def _ws(args: argparse.Namespace):
    from pathlib import Path

    return Path(args.workspace) if getattr(args, "workspace", None) else None


def cmd_interpret(args: argparse.Namespace) -> int:
    from pathlib import Path

    from . import anthropic_adapter, interpret

    try:
        if args.action == "prepare":
            return _emit({"ok": True, **interpret.prepare(args.asset_id, for_judge=args.for_judge, workspace=_ws(args))})
        if args.action == "estimate":
            pk = interpret.load_packet(args.asset_id, _ws(args))
            return _emit({"ok": True, "asset_id": args.asset_id, "packet_hash": pk["packet_hash"], "max_usd": args.max_usd,
                          **interpret.estimate_anthropic(pk, args.model)})
        if args.action == "ingest":
            if not args.answer:
                return _emit(exit_codes.error_payload(exit_codes.USAGE, "ingest needs the answer file path"), exit_codes.USAGE)
            res = interpret.ingest_answer(args.asset_id, Path(args.answer), args.judge, workspace=_ws(args))
            return _emit(res, exit_codes.OK if res["ok"] else exit_codes.VALIDATION)
        if args.action == "run":
            res = interpret.run(args.asset_id, args.provider, model=args.model, max_usd=args.max_usd, skip_grok=args.skip_grok,
                                fixture_file=Path(args.fixture) if args.fixture else None, workspace=_ws(args), rerun=args.rerun)
            return _emit(res, exit_codes.OK if res["ok"] else exit_codes.PARTIAL)
    except interpret.InterpretError as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.VALIDATION)
        return _emit(exit_codes.error_payload(code, str(exc), retryable=exc.retryable), code)
    except anthropic_adapter.AdapterError as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.PROVIDER)
        return _emit(exit_codes.error_payload(code, str(exc), retryable=exc.retryable), code)
    except ImportError as exc:
        return _emit(exit_codes.error_payload(exit_codes.VALIDATION, f"missing dependency: {exc}; install the 'interpret' extra"), exit_codes.VALIDATION)
    return _emit(exit_codes.error_payload(exit_codes.USAGE, "unknown interpret action"), exit_codes.USAGE)


def cmd_validate(args: argparse.Namespace) -> int:
    from . import claims

    try:
        report = claims.validate_asset(args.asset_id, workspace=_ws(args))
    except claims.ClaimsError as exc:
        return _emit(exit_codes.error_payload(exit_codes.VALIDATION, str(exc)), exit_codes.VALIDATION)
    return _emit(report, exit_codes.OK if report["ok"] else exit_codes.VALIDATION)


def cmd_claims(args: argparse.Namespace) -> int:
    from . import claims

    rows = claims.list_claims(args.asset_id, kind=args.kind, status=args.status, source=args.source, workspace=_ws(args))
    brief = [{k: c.get(k) for k in ("claim_id", "term_id", "claim_kind", "source", "unit_id", "review_status", "single_judge", "disagreement_group", "corrected_term_id")} for c in rows]
    return _emit({"ok": True, "asset_id": args.asset_id, "count": len(rows), "claims": brief if not args.full else rows})


def cmd_review(args: argparse.Namespace) -> int:
    import os
    from pathlib import Path

    from . import claims

    author = args.author or os.environ.get("IRIS_REVIEWER", "user")
    if args.answer:
        from . import review_sheet

        try:
            res = review_sheet.apply_answer(args.answer, author, workspace=_ws(args))
        except review_sheet.SheetError as exc:
            code = exit_codes.USAGE if exc.code == "usage" else exit_codes.VALIDATION
            return _emit(exit_codes.error_payload(code, str(exc)), code)
        return _emit(res, exit_codes.OK if res["ok"] else exit_codes.VALIDATION)
    try:
        if args.batch:
            decisions = []
            for n, line in enumerate(Path(args.batch).read_text(encoding="utf-8").splitlines(), start=1):
                try:
                    decisions.extend(claims.parse_batch_line(line))
                except claims.ClaimsError as exc:
                    return _emit(exit_codes.error_payload(exit_codes.USAGE, f"line {n}: {exc}"), exit_codes.USAGE)
        else:
            if not args.claim_ids or not args.status:
                return _emit(exit_codes.error_payload(exit_codes.USAGE, "review needs <claim_id|range> --status ... or --batch <file>"), exit_codes.USAGE)
            decisions = [{"claim_id": cid, "status": args.status, "value": args.value, "reason": args.reason} for cid in claims.expand_ids(args.claim_ids)]
    except claims.ClaimsError as exc:
        return _emit(exit_codes.error_payload(exit_codes.USAGE, str(exc)), exit_codes.USAGE)
    res = claims.apply_decisions(decisions, author, workspace=_ws(args))
    return _emit(res, exit_codes.OK if res["ok"] else exit_codes.VALIDATION)


def cmd_review_sheet(args: argparse.Namespace) -> int:
    from . import claims, review_sheet

    try:
        res = review_sheet.make_sheet(args.asset_id, workspace=_ws(args))
    except (review_sheet.SheetError, claims.ClaimsError) as exc:
        return _emit(exit_codes.error_payload(exit_codes.VALIDATION, str(exc)), exit_codes.VALIDATION)
    return _emit(res)


def cmd_ledger(args: argparse.Namespace) -> int:
    from . import ledger

    return _emit({"ok": True, **ledger.summary(workspace=_ws(args), month=args.month)})


def cmd_style(args: argparse.Namespace) -> int:
    from . import style

    try:
        if args.action == "build":
            sid = args.style_id_opt or args.style_id
            if not args.from_refs or not sid:
                return _emit(exit_codes.error_payload(exit_codes.USAGE, "style build needs --from <asset ids> and --style-id <id>"), exit_codes.USAGE)
            res = style.build([a.strip() for a in args.from_refs.split(",") if a.strip()], sid, workspace=_ws(args))
            return _emit(res, exit_codes.OK if res["ok"] else exit_codes.VALIDATION)
        if not args.style_id:
            return _emit(exit_codes.error_payload(exit_codes.USAGE, f"style {args.action} needs a style id"), exit_codes.USAGE)
        if args.action == "lint":
            res = style.lint(args.style_id, workspace=_ws(args))
            return _emit(res, exit_codes.OK if res["ok"] else exit_codes.VALIDATION)
        if args.action == "approve":
            author = args.author or os.environ.get("IRIS_REVIEWER", "")
            res = style.approve(args.style_id, author, workspace=_ws(args))
            return _emit(res, exit_codes.OK if res["ok"] else exit_codes.VALIDATION)
    except style.StyleError as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.VALIDATION)
        return _emit(exit_codes.error_payload(code, str(exc)), code)
    return _emit(exit_codes.error_payload(exit_codes.USAGE, "unknown style action"), exit_codes.USAGE)


def cmd_check(args: argparse.Namespace) -> int:
    from . import check, style

    try:
        res = check.check(args.clip, args.against, rights=args.rights, mode=args.mode, workspace=_ws(args))
    except (check.CheckError, style.StyleError) as exc:
        code = _CODE_BY_NAME.get(exc.code, exit_codes.VALIDATION)
        return _emit(exit_codes.error_payload(code, str(exc)), code)
    return _emit({"ok": True, **res})


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

    ing = sub.add_parser("ingest", help="Register a reference from a URL or file")
    ing.add_argument("source", help="http(s) URL or local file path")
    ing.add_argument("--rights", required=True, choices=["study", "own", "licensed"])
    ing.add_argument("--copy", action="store_true", help="copy a local file into the workspace instead of referencing it")
    ing.add_argument("--json", action="store_true", help="(default) JSON output")
    ing.set_defaults(func=cmd_ingest)

    an = sub.add_parser("analyze", help="Measure a registered asset (milestone 1: index + per-frame measurement)")
    an.add_argument("asset_id")
    an.add_argument("--mode", choices=["economy", "strict"], default="economy")
    an.add_argument("--force", action="store_true", help="recompute the derived stages of an existing job (index and measurement are kept)")
    an.add_argument("--stages", help="with --force: comma-separated subset to recompute (dependents are recomputed too), e.g. text,audio")
    an.add_argument("--json", action="store_true")
    an.set_defaults(func=cmd_analyze)

    jb = sub.add_parser("jobs", help="Inspect, resume or cancel jobs")
    jb.add_argument("action", choices=["status", "resume", "cancel", "list"])
    jb.add_argument("job_id", nargs="?")
    jb.add_argument("--asset-id")
    jb.add_argument("--json", action="store_true")
    jb.set_defaults(func=cmd_jobs)

    ip = sub.add_parser("interpret", help="Prepare a packet, ingest a judge's answer, or run the API judge")
    ip.add_argument("action", choices=["prepare", "ingest", "estimate", "run"])
    ip.add_argument("asset_id")
    ip.add_argument("answer", nargs="?", help="(ingest) path to the judge's answer JSON")
    ip.add_argument("--for", dest="for_judge", choices=["grok", "anthropic"], default="anthropic", help="(prepare) which judge will read it; both share one packet")
    ip.add_argument("--judge", choices=["grok", "anthropic", "fixture"], default="grok", help="(ingest) which judge wrote the answer")
    ip.add_argument("--provider", choices=["anthropic", "fixture"], default="anthropic", help="(run)")
    ip.add_argument("--model", help="(run) exact model id; default claude-sonnet-5-5")
    ip.add_argument("--max-usd", type=float, default=1.5, help="(run) per-reference cap in USD")
    ip.add_argument("--skip-grok", action="store_true", help="(run) proceed without the Grok judge's answer")
    ip.add_argument("--rerun", action="store_true", help="(run) pay again for a packet the API judge already answered")
    ip.add_argument("--fixture", help="(run --provider fixture) answer file to replay")
    ip.add_argument("--workspace")
    ip.add_argument("--json", action="store_true")
    ip.set_defaults(func=cmd_interpret)

    va = sub.add_parser("validate", help="Build and validate claims and evidence for an asset")
    va.add_argument("asset_id")
    va.add_argument("--workspace")
    va.add_argument("--json", action="store_true")
    va.set_defaults(func=cmd_validate)

    cl = sub.add_parser("claims", help="List claims")
    cl.add_argument("action", choices=["list"])
    cl.add_argument("asset_id")
    cl.add_argument("--kind", choices=["measured", "estimated", "interpreted"])
    cl.add_argument("--status", choices=["pending", "needs_review", "accepted", "corrected", "rejected"])
    cl.add_argument("--source", choices=["code", "model"])
    cl.add_argument("--full", action="store_true")
    cl.add_argument("--workspace")
    cl.add_argument("--json", action="store_true")
    cl.set_defaults(func=cmd_claims)

    rv = sub.add_parser("review", help="Record human review decisions (append-only)")
    rv.add_argument("claim_ids", nargs="?", help="claim id, range c_000012-c_000040, or comma list")
    rv.add_argument("--status", choices=["accepted", "corrected", "rejected"])
    rv.add_argument("--value", help="(corrected) dimension=term")
    rv.add_argument("--reason")
    rv.add_argument("--batch", help="file with one decision per line: accept/reject/correct ...")
    rv.add_argument("--answer", help="the line the review sheet printed: iris-review <asset_id> <sheet_id> <codes>")
    rv.add_argument("--author")
    rv.add_argument("--workspace")
    rv.add_argument("--json", action="store_true")
    rv.set_defaults(func=cmd_review)

    rs = sub.add_parser("review-sheet", help="Write the review-by-exception sheet (HTML) for an asset")
    rs.add_argument("asset_id")
    rs.add_argument("--workspace")
    rs.add_argument("--json", action="store_true")
    rs.set_defaults(func=cmd_review_sheet)

    lg = sub.add_parser("ledger", help="Summarize model calls and cost")
    lg.add_argument("action", choices=["summary"])
    lg.add_argument("--month", help="YYYY-MM (default: current month)")
    lg.add_argument("--workspace")
    lg.add_argument("--json", action="store_true")
    lg.set_defaults(func=cmd_ledger)

    st = sub.add_parser("style", help="Build, lint or approve a Style Bible")
    st.add_argument("action", choices=["build", "lint", "approve"])
    st.add_argument("style_id", nargs="?", help="(lint, approve) style id, e.g. kinetic-editorial-v1")
    st.add_argument("--from", dest="from_refs", help="(build) comma-separated asset ids")
    st.add_argument("--style-id", dest="style_id_opt", help="(build) style id")
    st.add_argument("--author", help="(approve) who approves; default $IRIS_REVIEWER")
    st.add_argument("--workspace")
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_style)

    ck = sub.add_parser("check", help="Evaluate a clip against a Style Bible")
    ck.add_argument("clip", help="local mp4 path or URL")
    ck.add_argument("--against", required=True, help="style id")
    ck.add_argument("--rights", choices=["study", "own", "licensed"], default="own")
    ck.add_argument("--mode", choices=["economy", "strict"], default="economy")
    ck.add_argument("--workspace")
    ck.add_argument("--json", action="store_true")
    ck.set_defaults(func=cmd_check)

    for name, helptext in [
        ("query", "Search accepted claims and references"),
        ("report", "Export the HTML report"),
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
