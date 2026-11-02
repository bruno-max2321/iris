"""Review by exception: `iris review-sheet <asset_id>` and `iris review --answer "<line>"`.

The reviewer does not judge claims one by one. Undecided claims are folded into a few plain statements
per dimension, and only the disagreements that would change the result become questions:

- statement (default yes): the terms both judges agreed on (or the code estimated), one per term that
  covers at least STATEMENT_MIN_SHARE of the dimension's agreed runtime, with example keyframes.
  yes -> accept those claims, no -> reject them, skip -> leave them out of the Style Bible.
- question (default skip): judges disagree between two terms on some units, and resolving the dispute
  one way or the other changes the dimension's summary (top term or the set of statements).
  a / b -> accept that term on the disputed units and reject the other, x -> reject both, skip -> nothing.
- not asked: single-judge labels, minor terms and disputes that change nothing stay undecided, which
  means they never reach the Style Bible. Dimensions nobody could judge are listed in one line.

The sheet is a self-contained HTML page (thumbnails inline). Its Approve button produces one answer line,
`iris-review <asset_id> <sheet_id> <codes>`, one code per item in order. The CLI rebuilds the sheet from
the current claims and refuses the line when the sheet id no longer matches (claims changed, or the
answer was already applied), so a line can be applied once and only to the sheet the reviewer saw."""

from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import re
from pathlib import Path
from typing import Any

from . import claims as claims_mod
from . import evidence, ingest, paths, registry

STATEMENT_MIN_SHARE = 0.10
THUMB_LONG_SIDE = 320
THUMBS_PER_ITEM = 3
UNDECIDED = ("pending", "needs_review")

# plain-language headings; anything missing falls back to the registry description
QUESTIONS = {
    "camera.movement": "How the camera moves",
    "light.key": "Overall brightness mood",
    "light.side": "Which side the light falls from",
    "light.quality": "Hard or soft shadows",
    "light.direction": "Where the main light comes from",
    "light.scheme": "Lighting setup",
    "composition": "Visual techniques in the image",
    "optics": "Lens look (focus, blur, flare)",
    "material.surface": "Surfaces and materials on set",
    "typography.family_class": "Typeface style of the on-screen text",
    "narrative.function": "What the shots do in the story",
    "narrative.hook_type": "How the opening grabs attention",
    "style.medium": "Kind of image (filmed, generated, animated)",
    "montage.pacing": "Editing pace",
    "caption.cadence": "Caption rhythm",
}


class SheetError(RuntimeError):
    def __init__(self, message: str, code: str = "validation") -> None:
        super().__init__(message)
        self.code = code


def _ref_dir(asset_id: str, workspace: Path | None) -> Path:
    return (workspace or paths.workspace_root()) / "refs" / asset_id


def _weight(c: dict[str, Any]) -> float:
    span = c.get("time_span") or {}
    try:
        return max(1e-3, float(span["end_seconds"]) - float(span["start_seconds"]))
    except (KeyError, TypeError, ValueError):
        return 1.0


def _term(c: dict[str, Any]) -> str:
    return c["term_id"].split("=", 1)[1]


def heading(dim: str) -> str:
    if dim in QUESTIONS:
        return QUESTIONS[dim]
    desc = (registry.dimension(dim) or {}).get("description") or dim
    return desc.split(". ")[0].rstrip(".")


def term_label(dim: str, term: str) -> str:
    return term.replace("_", " ")


def term_definition(dim: str, term: str) -> str:
    card = registry.lexicon_card(f"{dim}={term}") or {}
    return card.get("definition") or ""


def _shares(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {t: w / total for t, w in weights.items()} if total > 0 else {}


def _summary(weights: dict[str, float]) -> tuple[str | None, frozenset]:
    """(top term, terms that would be statements) for a weight map."""
    sh = _shares(weights)
    if not sh:
        return None, frozenset()
    top = max(sh.items(), key=lambda kv: (kv[1], kv[0]))[0]
    return top, frozenset(t for t, s in sh.items() if s >= STATEMENT_MIN_SHARE)


def _units(cs: list[dict[str, Any]]) -> list[str | None]:
    return sorted({c.get("unit_id") for c in cs}, key=lambda u: (u is not None, u or ""))


def build_items(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    rows = [c for c in claims_mod.list_claims(asset_id, workspace=workspace)
            if c["review_status"] in UNDECIDED and c["claim_kind"] in ("estimated", "interpreted")]
    by_dim: dict[str, list[dict[str, Any]]] = {}
    for c in rows:
        by_dim.setdefault(c["dimension"], []).append(c)
    items: list[dict[str, Any]] = []
    not_asked: list[dict[str, Any]] = []
    order = list(QUESTIONS) + sorted(d for d in by_dim if d not in QUESTIONS)
    for dim in [d for d in order if d in by_dim]:
        cs = by_dim[dim]
        agreed = [c for c in cs if c["source"] == "code" or (c["review_status"] == "pending" and not c.get("single_judge"))]
        groups: dict[str, list[dict[str, Any]]] = {}
        for c in cs:
            if c["review_status"] == "needs_review" and c.get("disagreement_group"):
                groups.setdefault(c["disagreement_group"], []).append(c)
        weights: dict[str, float] = {}
        for c in agreed:
            weights[_term(c)] = weights.get(_term(c), 0.0) + _weight(c)
        used: set[str] = set()
        dim_items: list[dict[str, Any]] = []
        sh = _shares(weights)
        total_units = len(_units(cs))
        for term, share in sorted(sh.items(), key=lambda kv: (-kv[1], kv[0])):
            if share < STATEMENT_MIN_SHARE:
                continue
            members = sorted((c for c in agreed if _term(c) == term), key=lambda c: -_weight(c))
            used.update(c["claim_id"] for c in members)
            dim_items.append({"kind": "statement", "dimension": dim, "term": term, "share": round(share, 3),
                              "units": len(members), "units_total": total_units,
                              "source": "code" if all(c["source"] == "code" for c in members) else "judges",
                              "claim_ids": [c["claim_id"] for c in members], "example_units": [c.get("unit_id") for c in members[:THUMBS_PER_ITEM]],
                              "default": "y"})
        # the most contested pair of terms in this dimension
        pair_weight: dict[tuple[str, str], float] = {}
        for gcs in groups.values():
            terms = sorted({_term(c) for c in gcs})
            w = _weight(gcs[0])
            for i, a in enumerate(terms):
                for b in terms[i + 1:]:
                    pair_weight[(a, b)] = pair_weight.get((a, b), 0.0) + w
        if pair_weight:
            (a, b), _w = max(pair_weight.items(), key=lambda kv: (kv[1], kv[0]))
            covered = {g: gcs for g, gcs in groups.items() if {a, b} <= {_term(c) for c in gcs}}
            cw = sum(_weight(gcs[0]) for gcs in covered.values())
            wa, wb = dict(weights), dict(weights)
            wa[a] = wa.get(a, 0.0) + cw
            wb[b] = wb.get(b, 0.0) + cw
            if _summary(wa) != _summary(wb):
                claim_ids = {"a": [], "b": []}
                for gcs in covered.values():
                    for c in gcs:
                        if _term(c) == a:
                            claim_ids["a"].append(c["claim_id"])
                        elif _term(c) == b:
                            claim_ids["b"].append(c["claim_id"])
                units = sorted({gcs[0].get("unit_id") for gcs in covered.values()}, key=lambda u: (u is not None, u or ""))
                used.update(claim_ids["a"] + claim_ids["b"])
                dim_items.append({"kind": "question", "dimension": dim, "a": a, "b": b, "units": len(units), "units_total": total_units,
                                  "claim_ids": claim_ids, "example_units": units[:THUMBS_PER_ITEM + 1], "default": "s"})
        items.extend(dim_items)
        left = [c for c in cs if c["claim_id"] not in used]
        if left:
            not_asked.append({"dimension": dim, "claims": len(left)})
    body = [[it["kind"], it["dimension"], it.get("term") or [it["a"], it["b"]], it["claim_ids"]] for it in items]
    state = sorted([c["claim_id"], c["review_status"], c["term_id"]] for c in rows)
    sheet_id = hashlib.sha256(json.dumps([asset_id, body, state], sort_keys=True).encode()).hexdigest()[:12]
    return {"schema_version": "1.0.0", "asset_id": asset_id, "sheet_id": sheet_id, "items": items, "not_asked": not_asked,
            "claims_undecided": len(rows)}


# ------------------------------------------------------------------------------------------ thumbnails
def _thumbs(asset_id: str, units: set[str | None], workspace: Path | None) -> dict[str, str]:
    """shot_id -> data URI of its mid keyframe. Reuses interpret/images when present, else decodes the source."""
    from PIL import Image

    ref_dir = _ref_dir(asset_id, workspace)
    shots = {s["shot_id"]: s for s in ((evidence.load_docs(ref_dir).get("shots") or {}).get("shots") or [])}
    wanted = {u for u in units if u in shots}
    if None in units and shots:
        wanted.add(next(iter(shots)))
    out: dict[str, str] = {}

    def put(sid: str, im: Image.Image) -> None:
        im = im.convert("RGB")
        im.thumbnail((THUMB_LONG_SIDE, THUMB_LONG_SIDE))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=70)
        out[sid] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    missing = []
    for sid in sorted(wanted):
        p = ref_dir / "interpret" / "images" / f"keyframe_{sid}_mid.jpg"
        if p.exists():
            with Image.open(p) as im:
                put(sid, im)
        else:
            missing.append(sid)
    if missing:
        try:
            from . import decode

            manifest = ingest.load_manifest(asset_id, workspace)
            vid = (manifest.get("probe") or {}).get("video") or {}
            dw, dh = int(vid.get("display_width") or 0), int(vid.get("display_height") or 0)
            scale = THUMB_LONG_SIDE / max(dw, dh, 1)
            w, h = max(2, int(dw * scale) // 2 * 2), max(2, int(dh * scale) // 2 * 2)
            by_frame: dict[int, list[str]] = {}
            for sid in missing:
                by_frame.setdefault(int(shots[sid]["keyframes"]["mid"]), []).append(sid)
            for fid, rgb in decode.pick_frames_iter(ingest.source_path(manifest), sorted(by_frame), w, h):
                for sid in by_frame[fid]:
                    put(sid, Image.fromarray(rgb))
        except Exception:  # thumbnails are a convenience; the sheet still works without them
            pass
    return out


# ------------------------------------------------------------------------------------------ html
def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _imgs(units: list[str | None], thumbs: dict[str, str], first_shot: str | None) -> str:
    tags = []
    for u in units:
        sid = u if u is not None else first_shot
        if sid and sid in thumbs:
            tags.append(f'<figure><img src="{thumbs[sid]}" alt="{_e(sid)}"><figcaption>{_e(sid if u else "opening")}</figcaption></figure>')
    return f'<div class="imgs">{"".join(tags)}</div>' if tags else ""


def _statement_text(it: dict[str, Any]) -> str:
    if it["units_total"] == 1 and it["example_units"] == [None]:
        return f"<b>{_e(term_label(it['dimension'], it['term']))}</b>"
    return f"<b>{_e(term_label(it['dimension'], it['term']))}</b> in {it['units']} of {it['units_total']} shots ({round(it['share'] * 100)}% of that time)"


def render_html(sheet: dict[str, Any], thumbs: dict[str, str], first_shot: str | None) -> str:
    items = sheet["items"]
    nq = sum(1 for i in items if i["kind"] == "question")
    ns = len(items) - nq
    cards = []
    for n, it in enumerate(items):
        dim = it["dimension"]
        if it["kind"] == "question":
            opts = "".join(
                f'<div class="opt"><b>{k.upper()} · {_e(term_label(dim, t))}</b><span>{_e(term_definition(dim, t))}</span></div>'
                for k, t in (("a", it["a"]), ("b", it["b"])))
            buttons = "".join(f'<button data-v="{v}">{lab}</button>' for v, lab in (("a", "A"), ("b", "B"), ("x", "Neither"), ("s", "Don't know")))
            cards.append(f'<section class="card q" data-i="{n}" data-v="s"><h3>{_e(heading(dim))}</h3>'
                         f'<p>The two judges disagree on {it["units"]} shot{"s" if it["units"] != 1 else ""}. Which fits these images better?</p>'
                         f'{_imgs(it["example_units"], thumbs, first_shot)}{opts}<div class="btns">{buttons}</div></section>')
        else:
            who = "measured by the code" if it["source"] == "code" else "both judges agree"
            buttons = "".join(f'<button data-v="{v}">{lab}</button>' for v, lab in (("y", "Yes"), ("n", "No"), ("s", "Don't know")))
            cards.append(f'<section class="card s" data-i="{n}" data-v="y"><h3>{_e(heading(dim))}</h3>'
                         f'<p>{_statement_text(it)} <small>({who})</small></p><p class="def">{_e(term_definition(dim, it["term"]))}</p>'
                         f'{_imgs(it["example_units"], thumbs, first_shot)}<div class="btns">{buttons}</div></section>')
    skipped = ", ".join(f"{_e(heading(x['dimension']))} ({x['claims']})" for x in sheet["not_asked"]) or "nothing"
    defaults = "".join(it["default"] for it in items)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iris review</title><style>
:root{{--bg:#f6f6f4;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#deded9;--on:#1d1d1b;--onink:#fff;--q:#b5651d}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--card:#1f1f1d;--ink:#ecece8;--mute:#9a9a94;--line:#33332f;--on:#ecece8;--onink:#151514;--q:#e09a52}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,sans-serif}}
main{{max-width:720px;margin:0 auto;padding:16px 16px 120px}}h1{{font-size:20px;margin:4px 0}}h2{{font-size:15px;margin:22px 0 8px;color:var(--mute);font-weight:600}}
.lead{{color:var(--mute);margin:0 0 8px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0}}
.card.q{{border-left:4px solid var(--q)}}h3{{margin:0 0 4px;font-size:15px}}p{{margin:4px 0}}.def{{color:var(--mute);font-size:13px}}small{{color:var(--mute)}}
.imgs{{display:flex;gap:6px;overflow-x:auto;margin:8px 0}}figure{{margin:0}}img{{height:120px;border-radius:6px;display:block}}figcaption{{font-size:11px;color:var(--mute)}}
.opt{{margin:6px 0}}.opt span{{display:block;color:var(--mute);font-size:13px}}.btns{{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}}
button{{font:inherit;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}}
button.on{{background:var(--on);color:var(--onink);border-color:var(--on)}}
footer{{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px}}
footer div{{max-width:720px;margin:0 auto;display:flex;gap:8px;align-items:center}}#go{{background:var(--on);color:var(--onink);padding:10px 18px;font-weight:600}}
#line{{flex:1;font:12px ui-monospace,monospace;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-width:0}}
.skip{{color:var(--mute);font-size:13px}}</style></head><body><main>
<h1>Review {_e(sheet['asset_id'])}</h1>
<p class="lead">{nq} question{"s" if nq != 1 else ""} and {ns} statement{"s" if ns != 1 else ""}. Statements are pre-set to Yes, questions to Don't know: if nothing looks wrong, press Approve and paste the line to the bot. Anything you skip simply stays out of the Style Bible.</p>
{"<h2>Questions</h2>" if nq else ""}{"".join(c for c in cards if 'class="card q"' in c)}
{"<h2>Statements</h2>" if ns else ""}{"".join(c for c in cards if 'class="card s"' in c)}
<p class="skip">Not asked (one judge only, minor or not decidable): {skipped}.</p>
</main><footer><div><button id="go">Approve</button><input id="line" readonly value="iris-review {_e(sheet['asset_id'])} {_e(sheet['sheet_id'])} {defaults}"></div></footer>
<script>
const head="iris-review {_e(sheet['asset_id'])} {_e(sheet['sheet_id'])} ";
const cards=[...document.querySelectorAll('.card')].sort((a,b)=>a.dataset.i-b.dataset.i);
function sync(){{for(const c of cards)for(const b of c.querySelectorAll('button'))b.classList.toggle('on',b.dataset.v===c.dataset.v);
document.getElementById('line').value=head+cards.map(c=>c.dataset.v).join('');}}
for(const c of cards)for(const b of c.querySelectorAll('button'))b.onclick=()=>{{c.dataset.v=b.dataset.v;sync();}};
document.getElementById('go').onclick=async()=>{{const l=document.getElementById('line');l.select();
try{{await navigator.clipboard.writeText(l.value);document.getElementById('go').textContent='Copied';}}catch(e){{document.execCommand&&document.execCommand('copy');document.getElementById('go').textContent='Copy the line';}}}};
sync();</script></body></html>"""


def make_sheet(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    sheet = build_items(asset_id, workspace)
    units: set[str | None] = set()
    for it in sheet["items"]:
        units.update(it["example_units"])
    ref_dir = _ref_dir(asset_id, workspace)
    shots = (evidence.load_docs(ref_dir).get("shots") or {}).get("shots") or []
    first = shots[0]["shot_id"] if shots else None
    thumbs = _thumbs(asset_id, units, workspace)
    out = ref_dir / "review"
    out.mkdir(parents=True, exist_ok=True)
    (out / "sheet.json").write_text(json.dumps(sheet, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "sheet.html").write_text(render_html(sheet, thumbs, first), encoding="utf-8")
    q = sum(1 for i in sheet["items"] if i["kind"] == "question")
    return {"ok": True, "asset_id": asset_id, "sheet_id": sheet["sheet_id"], "questions": q, "statements": len(sheet["items"]) - q,
            "claims_covered": sum(len(i["claim_ids"]) if i["kind"] == "statement" else len(i["claim_ids"]["a"]) + len(i["claim_ids"]["b"]) for i in sheet["items"]),
            "claims_undecided": sheet["claims_undecided"], "not_asked": sheet["not_asked"], "html": str(out / "sheet.html")}


# ------------------------------------------------------------------------------------------ answer
_ANSWER = re.compile(r"^\s*iris-review\s+([A-Za-z0-9_]+)\s+([0-9a-f]{12})\s+([ynsabx]*)\s*$")


def decisions_from_answer(line: str, workspace: Path | None = None) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    m = _ANSWER.match(line or "")
    if not m:
        raise SheetError("not a review line; expected 'iris-review <asset_id> <sheet_id> <codes>' exactly as the sheet printed it", "usage")
    asset_id, sheet_id, codes = m.groups()
    sheet = build_items(asset_id, workspace)
    if sheet["sheet_id"] != sheet_id:
        raise SheetError("this line belongs to an older sheet: the claims changed or the line was already applied; make a new sheet with iris review-sheet")
    items = sheet["items"]
    if len(codes) != len(items):
        raise SheetError(f"the line has {len(codes)} answers, the sheet has {len(items)} items", "usage")
    decisions: list[dict[str, Any]] = []
    summary: dict[str, int] = {"yes": 0, "no": 0, "chosen": 0, "neither": 0, "skipped": 0}
    tag = f"review sheet {sheet_id}"
    for it, code in zip(items, codes):
        dim = it["dimension"]
        if it["kind"] == "statement":
            if code not in "yns":
                raise SheetError(f"{dim}: a statement takes y, n or s, got {code!r}", "usage")
            if code == "y":
                decisions += [{"claim_id": c, "status": "accepted", "value": None, "reason": f"{tag}: confirmed"} for c in it["claim_ids"]]
                summary["yes"] += 1
            elif code == "n":
                decisions += [{"claim_id": c, "status": "rejected", "value": None, "reason": f"{tag}: reviewer says {it['term']} does not match"} for c in it["claim_ids"]]
                summary["no"] += 1
            else:
                summary["skipped"] += 1
        else:
            if code not in "abxs":
                raise SheetError(f"{dim}: a question takes a, b, x or s, got {code!r}", "usage")
            if code in "ab":
                win, lose = (it["a"], it["b"]) if code == "a" else (it["b"], it["a"])
                kw, kl = ("a", "b") if code == "a" else ("b", "a")
                decisions += [{"claim_id": c, "status": "accepted", "value": None, "reason": f"{tag}: reviewer chose {win} over {lose}"} for c in it["claim_ids"][kw]]
                decisions += [{"claim_id": c, "status": "rejected", "value": None, "reason": f"{tag}: reviewer chose {win} over {lose}"} for c in it["claim_ids"][kl]]
                summary["chosen"] += 1
            elif code == "x":
                decisions += [{"claim_id": c, "status": "rejected", "value": None, "reason": f"{tag}: reviewer says neither {it['a']} nor {it['b']}"}
                              for c in it["claim_ids"]["a"] + it["claim_ids"]["b"]]
                summary["neither"] += 1
            else:
                summary["skipped"] += 1
    return asset_id, decisions, summary


def apply_answer(line: str, author: str, workspace: Path | None = None) -> dict[str, Any]:
    asset_id, decisions, summary = decisions_from_answer(line, workspace)
    res = claims_mod.apply_decisions(decisions, author, workspace=workspace)
    counts: dict[str, int] = {}
    for r in res["recorded"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"ok": res["ok"], "asset_id": asset_id, "author": author, "answers": summary, "recorded": counts, "errors": res["errors"]}
