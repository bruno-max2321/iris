"""Stage N: `iris report export <asset_id> [--output DIR]`, a local, self-contained HTML report.

Every conclusion links to its evidence and back: a claim lists its evidence ids as links to the evidence
section, where each entry shows the stage file, the pointer inside it and the measured value (with the
keyframe for frame evidence) and links to the shot it belongs to; a shot row lists the claims about it.
Review history (who decided, when, why) and each judge's own answer sit next to every claim. Nothing is
recomputed: the report reads the stage outputs, the evidence index, the claims and the review events."""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import evidence, ingest, ledger, paths, review_sheet
from .store import Store

METHOD_VERSION = "report@0.1.0"
JUDGE_NAMES = {"grok": "Grok", "anthropic": "Claude", "fixture": "Fixture"}


class ReportError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _e(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _anchor(eid: str) -> str:
    return "ev-" + re.sub(r"[^A-Za-z0-9_-]", "-", eid)


def _fmt_value(v: Any, limit: int = 220) -> str:
    text = json.dumps(v, ensure_ascii=False, separators=(", ", ": ")) if not isinstance(v, str) else v
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _effective(c: dict[str, Any]) -> str:
    return c["corrected_term_id"] if c.get("review_status") == "corrected" and c.get("corrected_term_id") else c["term_id"]


def _exposure(v: Any) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k} {x}" for k, x in v.items() if k not in ("cost_usd",) and x not in (None, ""))
    return "" if v is None else str(v)


def _shot_of(eid: str) -> str | None:
    parts = eid.split(":")
    if len(parts) >= 2 and parts[0] in ("shot", "keyframe", "motion", "light", "color") and re.fullmatch(r"s\d{3,}", parts[1]):
        return parts[1]
    return None


def _styles_using(asset_id: str, ws: Path) -> list[dict[str, Any]]:
    out = []
    for p in sorted((ws / "styles").glob("*/style_bible.json")):
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if asset_id in (b.get("built_from") or []):
            out.append({"style_id": b.get("style_id") or p.parent.name, "status": b.get("status")})
    return out


def _ledger_cost(asset_id: str, ws: Path) -> float:
    return round(sum(float(r.get("cost_usd") or 0.0) for r in ledger.entries(ws) if r.get("asset_id") == asset_id), 6)


def collect(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    ws = workspace or paths.workspace_root()
    ref_dir = ws / "refs" / asset_id
    if not (ref_dir / "manifest.json").exists():
        raise ReportError(f"unknown asset {asset_id}", "usage")
    docs = evidence.load_docs(ref_dir)
    if not docs.get("shots"):
        raise ReportError("analyze has not produced shots.json for this asset")
    idx = evidence.build_index(docs)
    store = Store(ws)
    try:
        claims = store.list_claims(asset_id)
        events = {c["claim_id"]: store.review_events(c["claim_id"]) for c in claims}
    finally:
        store.close()
    validate = json.loads((ref_dir / "validate.json").read_text(encoding="utf-8")) if (ref_dir / "validate.json").exists() else {}
    return {"ws": ws, "ref_dir": ref_dir, "manifest": ingest.load_manifest(asset_id, ws), "docs": docs, "idx": idx,
            "claims": claims, "events": events, "validate": validate, "styles": _styles_using(asset_id, ws), "cost_usd": _ledger_cost(asset_id, ws)}


def _claim_row(c: dict[str, Any], events: list[dict[str, Any]], idx: dict[str, Any]) -> str:
    eff = _effective(c)
    dim, term = eff.split("=", 1)
    unit = c.get("unit_id")
    span = c.get("time_span") or {}
    when = f"{float(span.get('start_seconds', 0)):.2f}-{float(span.get('end_seconds', 0)):.2f} s" if span else ""
    unit_html = f'<a href="#shot-{_e(unit)}">{_e(unit)}</a>' if unit else _e(c.get("temporal_unit") or "video")
    ev_links = " ".join(
        f'<a class="ev" href="#{_anchor(e)}">{_e(e)}</a>' if e in idx else f'<span class="ev missing" title="not in the current evidence index">{_e(e)}</span>'
        for e in c.get("evidence_ids") or [])
    if c["source"] == "code":
        who = f"code ({_e(c.get('method_version'))})"
    else:
        who = "; ".join(f"{JUDGE_NAMES.get(j, j)}: {_e(v if v is not None else 'did not answer')}" for j, v in (c.get("judges") or {}).items())
    corrected = f' <span class="was">was {_e(c["term_id"].split("=", 1)[1])}</span>' if eff != c["term_id"] else ""
    hist = "".join(f"<li>{_e(ev['ts'])} · <b>{_e(ev['status'])}</b> by {_e(ev['author'])}{(' → ' + _e(ev['value'])) if ev.get('value') else ''}"
                   f"{(': ' + _e(ev['reason'])) if ev.get('reason') else ''}</li>" for ev in events) or "<li>no decision yet</li>"
    lim = "".join(f"<li>{_e(x)}</li>" for x in c.get("limitations") or [])
    return (f'<tr id="claim-{_e(c["claim_id"])}" class="st-{_e(c["review_status"])}"><td><b>{_e(term.replace("_", " "))}</b>{corrected}'
            f'<div class="sub">{_e(c["claim_id"])} · {_e(c["claim_kind"])}</div></td>'
            f'<td><span class="badge {_e(c["review_status"])}">{_e(c["review_status"])}</span></td><td>{unit_html}<div class="sub">{_e(when)}</div></td>'
            f'<td class="small">{who}</td><td class="small">{ev_links}</td>'
            f'<td><details><summary>history</summary><ul>{hist}</ul>{("<b>Limitations</b><ul>" + lim + "</ul>") if lim else ""}</details></td></tr>')


def render(data: dict[str, Any], out_dir: Path) -> str:
    m, docs, idx, claims = data["manifest"], data["docs"], data["idx"], data["claims"]
    asset_id = m["asset_id"]
    shots = docs["shots"].get("shots") or []
    montage = docs["shots"].get("montage") or {}
    cov = docs.get("coverage") or {}
    motion = {x["shot_id"]: x for x in (docs.get("motion") or {}).get("shots", [])}
    color = {x["shot_id"]: x for x in (docs.get("color") or {}).get("shots", [])}
    thumbs = review_sheet._thumbs(asset_id, {s["shot_id"] for s in shots}, data["ws"])
    by_shot: dict[str, list[dict[str, Any]]] = {}
    for c in claims:
        if c.get("unit_id"):
            by_shot.setdefault(c["unit_id"], []).append(c)
    cited = sorted({e for c in claims for e in c.get("evidence_ids") or [] if e in idx})
    citing: dict[str, list[str]] = {}
    for c in claims:
        for e in c.get("evidence_ids") or []:
            citing.setdefault(e, []).append(c["claim_id"])

    # conclusions, grouped by dimension, decided first
    order = {"accepted": 0, "corrected": 1, "needs_review": 2, "pending": 3, "rejected": 4}
    dims: dict[str, list[dict[str, Any]]] = {}
    for c in sorted(claims, key=lambda c: (order.get(c["review_status"], 9), c["claim_id"])):
        dims.setdefault(_effective(c).split("=", 1)[0], []).append(c)
    concl = []
    for dim in sorted(dims, key=lambda d: (list(review_sheet.QUESTIONS).index(d) if d in review_sheet.QUESTIONS else 99, d)):
        rows = "".join(_claim_row(c, data["events"].get(c["claim_id"], []), idx) for c in dims[dim])
        counts = {s: sum(1 for c in dims[dim] if c["review_status"] == s) for s in order}
        summary = ", ".join(f"{n} {s}" for s, n in counts.items() if n)
        concl.append(f'<details class="dim" {"open" if any(c["review_status"] in ("accepted", "corrected") for c in dims[dim]) else ""}>'
                     f'<summary><b>{_e(review_sheet.heading(dim))}</b> <span class="sub">{_e(dim)} · {_e(summary)}</span></summary>'
                     f'<table><tr><th>Conclusion</th><th>Status</th><th>Where</th><th>Who said it</th><th>Evidence</th><th></th></tr>{rows}</table></details>')

    # shots
    shot_rows = []
    for s in shots:
        sid = s["shot_id"]
        mo, co = motion.get(sid) or {}, color.get(sid) or {}
        bg = ((co.get("regions") or {}).get("background") or {}).get("palette") or []
        sw = "".join(f'<span class="sw" style="background:{_e(h)}" title="{_e(h)}"></span>' for h in bg[:4])
        light = co.get("light") or {}
        img = f'<img src="{thumbs[sid]}" alt="{_e(sid)}">' if sid in thumbs else ""
        cl = " ".join(f'<a href="#claim-{_e(c["claim_id"])}" class="chip {_e(c["review_status"])}">{_e(_effective(c).split("=", 1)[1].replace("_", " "))}</a>'
                      for c in sorted(by_shot.get(sid, []), key=lambda c: c["claim_id"]))
        shot_rows.append(f'<tr id="shot-{_e(sid)}"><td>{img}</td><td><b>{_e(sid)}</b><div class="sub">{float(s["t_in"]):.2f}-{float(s["t_out"]):.2f} s · '
                         f'{float(s["duration_s"]):.2f} s</div><div class="sub">frames {_e(s["frame_first"])}-{_e(s["frame_last_inclusive"])}</div></td>'
                         f'<td class="small">camera {_e(mo.get("class"))}<br>light {_e(light.get("key"))}, {_e(light.get("side"))}, {_e(light.get("edge"))}<br>{sw}</td>'
                         f'<td class="small">{cl}</td></tr>')

    # captions
    text = docs.get("text") or {}
    cap_rows = []
    by_track = {t["track_id"]: t for t in text.get("tracks") or []}
    for b in text.get("blocks") or []:
        ocr = [by_track[t].get("text_ocr") for t in b.get("track_ids") or [] if t in by_track and by_track[t].get("text_ocr")]
        links = " ".join(f'<a class="ev" href="#{_anchor("text:" + t)}">{_e(t)}</a>' if f"text:{t}" in idx else _e(t) for t in b.get("track_ids") or [])
        cap_rows.append(f'<tr><td class="small">{_e(b.get("frame_first_seen"))}-{_e(b.get("frame_last_seen"))}</td><td>{_e(b.get("text"))}'
                        f'{("<div class=sub>OCR read: " + _e(" / ".join(ocr)) + "</div>") if ocr else ""}</td>'
                        f'<td class="small">{_e(b.get("zone"))} · {_e(b.get("lines"))} line(s) · {_e(b.get("words"))} words</td><td class="small">{links}</td></tr>')
    dropped = len(text.get("dropped") or [])

    # evidence
    ev_rows = []
    for e in sorted(set(cited) | {f"text:{t}" for t in by_track if f"text:{t}" in idx}):
        ent = idx[e]
        sid = _shot_of(e)
        img = ""
        if ent["kind"] == "frame" and sid:
            which = e.split(":")[2]
            p = data["ref_dir"] / "interpret" / "images" / f"keyframe_{sid}_{which}.jpg"
            if not p.exists():
                p = data["ref_dir"] / "evidence_frames" / f"keyframe_{sid}_{which}.jpg"
            if which == "mid" and sid in thumbs:
                img = f'<img src="{thumbs[sid]}" alt="{_e(e)}">'
            elif p.exists():
                img = f'<a href="{_e(os.path.relpath(p, out_dir))}">open keyframe</a>'
        elif ent["kind"] == "image":
            p = data["ref_dir"] / (ent.get("value") or {}).get("path", "")
            img = f'<a href="{_e(os.path.relpath(p, out_dir))}">open image</a>' if p.exists() else ""
        back = " ".join(f'<a href="#claim-{_e(c)}">{_e(c)}</a>' for c in sorted(set(citing.get(e, []))))
        ev_rows.append(f'<tr id="{_anchor(e)}"><td><b>{_e(e)}</b>{(" · <a href=#shot-" + _e(sid) + ">" + _e(sid) + "</a>") if sid else ""}</td>'
                       f'<td class="small">{_e(ent["file"])}<div class="sub">{_e(ent["pointer"])}</div></td><td class="small mono">{_e(_fmt_value(ent.get("value")))}</td>'
                       f'<td>{img}</td><td class="small">{back}</td></tr>')

    val = data["validate"]
    agree = val.get("agreement") or {}
    stages = "".join(f"<li>{_e(k)}: {_e(v.get('status'))}{(' — ' + _e(v.get('reason'))) if v.get('reason') else ''}</li>" for k, v in (cov.get("stages") or {}).items())
    src = m.get("source") or {}
    styles = ", ".join(f"{_e(s['style_id'])} ({_e(s['status'])})" for s in data["styles"]) or "none yet"
    n_dec = sum(1 for c in claims if c["review_status"] in ("accepted", "corrected"))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iris report {_e(asset_id)}</title><style>
:root{{--bg:#f6f6f4;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#deded9;--acc:#2f6f4f;--warn:#b5651d;--bad:#a33}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--card:#1f1f1d;--ink:#ecece8;--mute:#9a9a94;--line:#33332f;--acc:#6fbf8f;--warn:#e09a52;--bad:#e06b6b}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:16px}}h1{{font-size:20px;margin:4px 0}}h2{{font-size:16px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}}
a{{color:var(--acc)}}table{{width:100%;border-collapse:collapse;background:var(--card)}}td,th{{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top;text-align:left}}
th{{font-size:12px;color:var(--mute);font-weight:600}}.sub{{color:var(--mute);font-size:12px}}.small{{font-size:12px}}.mono{{font-family:ui-monospace,monospace;word-break:break-all}}
img{{height:96px;border-radius:4px;display:block}}.sw{{display:inline-block;width:14px;height:14px;border-radius:3px;margin-right:2px;border:1px solid var(--line)}}
.badge{{font-size:11px;padding:1px 6px;border-radius:9px;border:1px solid var(--line)}}.badge.accepted,.badge.corrected{{color:var(--acc);border-color:var(--acc)}}
.badge.needs_review{{color:var(--warn);border-color:var(--warn)}}.badge.rejected{{color:var(--bad);border-color:var(--bad)}}
.chip{{display:inline-block;font-size:11px;padding:0 6px;margin:1px;border-radius:9px;border:1px solid var(--line);text-decoration:none}}.chip.rejected{{text-decoration:line-through;opacity:.6}}
.ev{{font-family:ui-monospace,monospace;font-size:11px;margin-right:4px}}.missing{{color:var(--bad)}}.was{{color:var(--mute);font-size:12px;text-decoration:line-through}}
details.dim{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin:8px 0}}details.dim summary{{cursor:pointer}}
tr.st-rejected td{{opacity:.6}}:target{{outline:2px solid var(--acc)}}.facts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}}
.fact{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}}.fact b{{display:block;font-size:12px;color:var(--mute);font-weight:600}}
</style></head><body><main>
<h1>Iris report · {_e(asset_id)}</h1>
<p class="sub">Source: {_e(src.get("platform"))} {_e(src.get("input"))} · rights {_e(m.get("rights"))} · generated {datetime.now(timezone.utc).isoformat(timespec="seconds")} by {METHOD_VERSION}.
Every conclusion links to its evidence; every evidence entry links back to the conclusions that cite it and to its shot.</p>
<div class="facts">
<div class="fact"><b>Coverage</b>decode {_e(cov.get("decode"))} · measurement {_e(cov.get("measurement"))} · model exposure {_e(_exposure(cov.get("model_exposure")))}<br>{_e(cov.get("decoded_frames"))} of {_e(cov.get("expected_frames"))} frames</div>
<div class="fact"><b>Montage</b>{len(shots)} shots · {_e(montage.get("duration_s"))} s · {_e((montage.get("cuts_per_s") or {}).get("overall"))} cuts/s</div>
<div class="fact"><b>Judges</b>{_e(", ".join(val.get("judges_present") or []) or "none")} · exact agreement {_e(agree.get("exact_rate"))} on {_e(agree.get("units_compared"))} units · API cost {_e(data["cost_usd"])} USD</div>
<div class="fact"><b>Conclusions</b>{len(claims)} claims · {n_dec} accepted or corrected · Style Bibles: {styles}</div>
</div>
<details><summary class="sub">Stages</summary><ul class="small">{stages}</ul></details>
<h2>Conclusions</h2>{"".join(concl) or "<p class=sub>No claims yet: run iris validate.</p>"}
<h2>Shots</h2><table><tr><th></th><th>Shot</th><th>Measured</th><th>Conclusions</th></tr>{"".join(shot_rows)}</table>
<h2>Captions</h2><p class="sub">{len(text.get("blocks") or [])} caption blocks · {len(by_track)} text tracks · {dropped} OCR tracks dropped as junk · {_e((text.get("transcript_repair") or {}).get("repaired_tracks", 0))} lines spelled from the transcript</p>
<table><tr><th>Frames</th><th>Text</th><th>Layout</th><th>Tracks</th></tr>{"".join(cap_rows)}</table>
<h2>Evidence</h2><table><tr><th>Id</th><th>Source</th><th>Value</th><th></th><th>Cited by</th></tr>{"".join(ev_rows)}</table>
</main></body></html>"""


def export(asset_id: str, output: str | None = None, workspace: Path | None = None) -> dict[str, Any]:
    data = collect(asset_id, workspace)
    out_dir = Path(output).expanduser().resolve() if output else data["ref_dir"] / "report"
    out_dir.mkdir(parents=True, exist_ok=True)
    page = render(data, out_dir)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    links = re.findall(r'href="#([^"]+)"', page)
    ids = set(re.findall(r'id="([^"]+)"', page))
    broken = sorted({l for l in links if l not in ids})
    return {"ok": not broken, "asset_id": asset_id, "path": str(out_dir / "index.html"), "claims": len(data["claims"]),
            "evidence_entries": page.count('<tr id="ev-'), "broken_links": broken, "bytes": len(page.encode())}
