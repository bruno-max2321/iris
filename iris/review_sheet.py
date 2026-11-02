"""Review by exception: `iris review-sheet <asset_id>` and `iris review --answer "<line>"`.

The reviewer does not judge claims one by one, and is never a third approval of what both judges
already said: `make_sheet` first accepts every label Grok and Claude agree on (author POLICY_AUTHOR,
the user's standing rule). What is left is folded into a few plain items per dimension, and only the
disagreements that would change the result become questions:

- statement (default yes): code estimates no judge checked, one per term that
  covers at least STATEMENT_MIN_SHARE of the dimension's agreed runtime, with example keyframes.
  yes -> accept those claims, no -> reject them, skip -> leave them out of the Style Bible.
- question (default skip): judges disagree between two terms on some units, and resolving the dispute
  one way or the other changes the dimension's summary (top term or the set of statements).
  a / b -> accept that term on the disputed units and reject the other, z -> accept both (only where the
  dimension takes several terms), x -> reject both, skip -> nothing.
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


JUDGE_NAMES = {"grok": "Grok", "anthropic": "Claude", "fixture": "Fixture"}


def term_label(dim: str, term: str) -> str:
    return term.replace("_", " ")


def term_definition(dim: str, term: str) -> str:
    card = registry.lexicon_card(f"{dim}={term}") or {}
    return card.get("definition") or ""


def term_cues(dim: str, term: str) -> list[str]:
    card = registry.lexicon_card(f"{dim}={term}") or {}
    return [str(x) for x in (card.get("observable_cues") or [])][:2]


def term_counterexamples(dim: str, term: str) -> list[str]:
    """Plain 'not to be confused with' lines; registry entries are {confused_with, distinguish} or text."""
    card = registry.lexicon_card(f"{dim}={term}") or {}
    out = []
    for x in (card.get("counterexamples") or [])[:1]:
        if isinstance(x, dict):
            other = str(x.get("confused_with") or "").split("=")[-1].replace("_", " ")
            why = str(x.get("distinguish") or "").strip()
            out.append(f"Not the same as {other}. {why}".strip() if other else why)
        else:
            out.append(str(x))
    return [o for o in out if o]


def allows_several(dim: str) -> bool:
    return (registry.dimension(dim) or {}).get("cardinality") != "single"


def _backers(cs: list[dict[str, Any]], term: str) -> list[str]:
    """Judges that proposed `term` on any of these claims, by display name."""
    names = set()
    for c in cs:
        for j, v in (c.get("judges") or {}).items():
            if v and v != "unclear" and term in v.split(","):
                names.add(JUDGE_NAMES.get(j, j))
    return sorted(names)


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


POLICY_AUTHOR = "policy:judges-agree"
DECIDED_OK = ("accepted", "corrected")


def _effective(c: dict[str, Any]) -> str:
    if c.get("review_status") == "corrected" and c.get("corrected_term_id"):
        return c["corrected_term_id"].split("=", 1)[1]
    return _term(c)


def judges_agree(c: dict[str, Any]) -> bool:
    """Both judges proposed this exact term for this unit (fusion marks it pending, not single-judge)."""
    return c["source"] == "model" and c["review_status"] == "pending" and not c.get("single_judge")


def auto_accept(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    """The user's standing rule: when Grok and Claude agree, the label is accepted without asking."""
    todo = [c for c in claims_mod.list_claims(asset_id, workspace=workspace) if judges_agree(c)]
    if not todo:
        return {"accepted": 0, "errors": []}
    res = claims_mod.apply_decisions([{"claim_id": c["claim_id"], "status": "accepted", "value": None, "reason": "Grok and Claude agree"} for c in todo],
                                     POLICY_AUTHOR, workspace=workspace)
    return {"accepted": len(res["recorded"]), "errors": res["errors"]}


def _settled(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per dimension, the terms already accepted or corrected (by the policy or by the reviewer), for the sheet's summary."""
    out: dict[str, dict[str, int]] = {}
    for c in rows:
        if c["review_status"] in DECIDED_OK:
            d = out.setdefault(c["dimension"], {})
            d[_effective(c)] = d.get(_effective(c), 0) + 1
    order = list(QUESTIONS) + sorted(d for d in out if d not in QUESTIONS)
    return [{"dimension": d, "terms": sorted(out[d].items(), key=lambda kv: (-kv[1], kv[0]))} for d in order if d in out]


def build_items(asset_id: str, workspace: Path | None = None) -> dict[str, Any]:
    every = [c for c in claims_mod.list_claims(asset_id, workspace=workspace) if c["claim_kind"] in ("estimated", "interpreted")]
    rows = [c for c in every if c["review_status"] in UNDECIDED]
    by_dim: dict[str, list[dict[str, Any]]] = {}
    for c in rows:
        by_dim.setdefault(c["dimension"], []).append(c)
    settled_by_dim: dict[str, list[dict[str, Any]]] = {}
    for c in every:
        if c["review_status"] in DECIDED_OK:
            settled_by_dim.setdefault(c["dimension"], []).append(c)
    items: list[dict[str, Any]] = []
    not_asked: list[dict[str, Any]] = []
    order = list(QUESTIONS) + sorted(d for d in by_dim if d not in QUESTIONS)
    for dim in [d for d in order if d in by_dim]:
        cs = by_dim[dim]
        agreed = [c for c in cs if c["source"] == "code" or judges_agree(c)]
        groups: dict[str, list[dict[str, Any]]] = {}
        for c in cs:
            if c["review_status"] == "needs_review" and c.get("disagreement_group"):
                groups.setdefault(c["disagreement_group"], []).append(c)
        weights: dict[str, float] = {}
        for c in agreed:
            weights[_term(c)] = weights.get(_term(c), 0.0) + _weight(c)
        # what is already settled counts when deciding whether a dispute could change the result
        context: dict[str, float] = dict(weights)
        for c in settled_by_dim.get(dim, []):
            context[_effective(c)] = context.get(_effective(c), 0.0) + _weight(c)
        used: set[str] = set()
        dim_items: list[dict[str, Any]] = []
        sh = _shares(weights)
        total_units = len(_units(cs + settled_by_dim.get(dim, [])))
        for term, share in sorted(sh.items(), key=lambda kv: (-kv[1], kv[0])):
            if share < STATEMENT_MIN_SHARE:
                continue
            members = sorted((c for c in agreed if _term(c) == term), key=lambda c: -_weight(c))
            used.update(c["claim_id"] for c in members)
            dim_items.append({"kind": "statement", "dimension": dim, "term": term, "share": round(share, 3),
                              "units": len(members), "units_total": total_units,
                              "source": "code" if all(c["source"] == "code" for c in members) else "judges",
                              "by": _backers(members, term),
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
            wa, wb = dict(context), dict(context)
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
                disputed = [c for gcs in covered.values() for c in gcs]
                dim_items.append({"kind": "question", "dimension": dim, "a": a, "b": b, "units": len(units), "units_total": total_units,
                                  "claim_ids": claim_ids, "example_units": units[:THUMBS_PER_ITEM + 1], "default": "s",
                                  "a_by": _backers(disputed, a), "b_by": _backers(disputed, b), "allow_both": allows_several(dim)})
        items.extend(dim_items)
        left = [c for c in cs if c["claim_id"] not in used]
        if left:
            not_asked.append({"dimension": dim, "claims": len(left)})
    body = [[it["kind"], it["dimension"], it.get("term") or [it["a"], it["b"]], it["claim_ids"]] for it in items]
    state = sorted([c["claim_id"], c["review_status"], c["term_id"]] for c in rows)
    sheet_id = hashlib.sha256(json.dumps([asset_id, body, state], sort_keys=True).encode()).hexdigest()[:12]
    return {"schema_version": "1.0.0", "asset_id": asset_id, "sheet_id": sheet_id, "items": items, "not_asked": not_asked,
            "settled": _settled(every), "claims_undecided": len(rows)}


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
        if not p.exists():
            p = ref_dir / "evidence_frames" / f"keyframe_{sid}_mid.jpg"  # saved by gc before an original goes
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


def _who(names: list[str]) -> str:
    if not names:
        return "a judge"
    return " and ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + " and " + names[-1]


def _shots_phrase(n: int) -> str:
    return "shot" if n == 1 else f"{n} shots"


def _explain(dim: str, term: str) -> str:
    """Meaning, what to look for in the photos, and what it is not."""
    parts = [f'<span class="mean">{_e(term_definition(dim, term))}</span>']
    cues = term_cues(dim, term)
    if cues:
        parts.append(f'<span class="look"><b>Look for:</b> {_e("; ".join(cues))}.</span>')
    for ce in term_counterexamples(dim, term):
        parts.append(f'<span class="look"><b>Careful:</b> {_e(ce)}</span>')
    return "".join(parts)


def _statement_text(it: dict[str, Any]) -> str:
    label = f"<b>{_e(term_label(it['dimension'], it['term']))}</b>"
    if it["units_total"] == 1 and it["example_units"] == [None]:
        where = "for the whole video"
    else:
        where = f"in {it['units']} of {it['units_total']} shots ({round(it['share'] * 100)}% of the time those shots last)"
    who = "The code measured" if it["source"] == "code" else f"{_who(it.get('by') or ['Grok', 'Claude'])} both say"  # judge statements only when auto-accept did not run
    return f"{who}: {label} {where}."


def _question_card(n: int, it: dict[str, Any], thumbs: dict[str, str], first_shot: str | None) -> str:
    dim, a, b = it["dimension"], it["a"], it["b"]
    la, lb = term_label(dim, a), term_label(dim, b)
    shots = _shots_phrase(it["units"])
    by_a, by_b = _who(it.get("a_by") or []), _who(it.get("b_by") or [])
    opts = (f'<div class="opt"><div class="optk">A · {_e(la)}</div><div class="optby">{_e(by_a)} chose this</div>{_explain(dim, a)}</div>'
            f'<div class="opt"><div class="optk">B · {_e(lb)}</div><div class="optby">{_e(by_b)} chose this</div>{_explain(dim, b)}</div>')
    choices = [("a", f"A · {la}", f"you see {la} more clearly than {lb}"),
               ("b", f"B · {lb}", f"you see {lb} more clearly than {la}")]
    if it.get("allow_both"):
        choices.append(("z", "Both", "you clearly see both (a shot can use several of these at once)"))
    choices += [("x", "Neither", "you see neither of them"),
                ("s", "Don't know", "you are not sure; these shots are simply left out, nothing is lost")]
    guide = "".join(f"<li><b>{_e(lab)}</b>: {_e(why)}</li>" for _v, lab, why in choices)
    buttons = "".join(f'<button data-v="{v}">{_e(lab)}</button>' for v, lab, _w in choices)
    return (f'<section class="card q" data-i="{n}" data-v="s"><h3>{_e(heading(dim))}</h3>'
            f'<p>{_e(_who(sorted(set((it.get("a_by") or []) + (it.get("b_by") or [])))))} looked at the same {shots} and gave different answers. '
            f'Look at the photos and pick what you see.</p>'
            f'{_imgs(it["example_units"], thumbs, first_shot)}{opts}<ul class="guide">{guide}</ul><div class="btns">{buttons}</div></section>')


def _statement_card(n: int, it: dict[str, Any], thumbs: dict[str, str], first_shot: str | None) -> str:
    dim = it["dimension"]
    choices = [("y", "Yes, right"), ("n", "No, wrong"), ("s", "Don't know")]
    buttons = "".join(f'<button data-v="{v}">{lab}</button>' for v, lab in choices)
    return (f'<section class="card s" data-i="{n}" data-v="y"><h3>{_e(heading(dim))}</h3>'
            f'<p>{_statement_text(it)}</p><div class="def">{_explain(dim, it["term"])}</div>'
            f'{_imgs(it["example_units"], thumbs, first_shot)}<div class="btns">{buttons}</div></section>')


def render_html(sheet: dict[str, Any], thumbs: dict[str, str], first_shot: str | None) -> str:
    items = sheet["items"]
    nq = sum(1 for i in items if i["kind"] == "question")
    ns = len(items) - nq
    cards = [(_question_card if it["kind"] == "question" else _statement_card)(n, it, thumbs, first_shot) for n, it in enumerate(items)]
    settled = sheet.get("settled") or []
    settled_html = ("<h2>Already accepted (Grok and Claude agree, or you decided before)</h2><ul class=\"settled\">"
                    + "".join(f"<li><b>{_e(heading(x['dimension']))}</b>: " + ", ".join(f"{_e(term_label(x['dimension'], t))} ({n})" for t, n in x["terms"][:6]) + "</li>" for x in settled)
                    + "</ul>") if settled else ""
    skipped = ", ".join(f"{_e(heading(x['dimension']))} ({x['claims']})" for x in sheet["not_asked"]) or "nothing"
    defaults = "".join(it["default"] for it in items)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Iris review</title><style>
:root{{--bg:#f6f6f4;--card:#fff;--ink:#1d1d1b;--mute:#6b6b66;--line:#deded9;--on:#1d1d1b;--onink:#fff;--q:#b5651d}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--card:#1f1f1d;--ink:#ecece8;--mute:#9a9a94;--line:#33332f;--on:#ecece8;--onink:#151514;--q:#e09a52}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,sans-serif}}
main{{max-width:720px;margin:0 auto;padding:16px 16px 120px}}h1{{font-size:20px;margin:4px 0}}h2{{font-size:15px;margin:22px 0 8px;color:var(--mute);font-weight:600}}
.lead{{color:var(--mute);margin:0 0 8px}}.lead b{{color:var(--ink)}}.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0}}
.card.q{{border-left:4px solid var(--q)}}h3{{margin:0 0 4px;font-size:15px}}p{{margin:4px 0}}.def{{color:var(--mute);font-size:13px}}small{{color:var(--mute)}}
.imgs{{display:flex;gap:6px;overflow-x:auto;margin:8px 0}}figure{{margin:0}}img{{height:120px;border-radius:6px;display:block}}figcaption{{font-size:11px;color:var(--mute)}}
.opt{{margin:10px 0;padding:8px 10px;border:1px solid var(--line);border-radius:8px}}.optk{{font-weight:600}}.optby{{font-size:12px;color:var(--q)}}.mean,.look{{display:block;font-size:13px;margin-top:2px}}.look{{color:var(--mute)}}.guide{{margin:8px 0 0;padding-left:18px;font-size:13px;color:var(--mute)}}.lead p{{margin:0 0 6px}}.btns{{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}}
button{{font:inherit;border:1px solid var(--line);background:transparent;color:var(--ink);border-radius:8px;padding:6px 12px;cursor:pointer}}
button.on{{background:var(--on);color:var(--onink);border-color:var(--on)}}
footer{{position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 16px}}
footer div{{max-width:720px;margin:0 auto;display:flex;gap:8px;align-items:center}}#go{{background:var(--on);color:var(--onink);padding:10px 18px;font-weight:600}}
#line{{flex:1;font:12px ui-monospace,monospace;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);min-width:0}}
.skip{{color:var(--mute);font-size:13px}}.settled{{font-size:13px;color:var(--mute);padding-left:18px}}.settled b{{color:var(--ink)}}</style></head><body><main>
<h1>Review {_e(sheet['asset_id'])}</h1>
<div class="lead"><p>Two AI judges, <b>Grok</b> and <b>Claude</b>, labelled every shot of this video without seeing each other's answers. <b>Where they agree, the label is already accepted</b>: you do not need to approve it again (listed at the bottom).</p>
<p>You only decide where there is doubt:</p>
<p>• <b>{nq} question{"s" if nq != 1 else ""}</b>: the judges disagree. Look at the photos and pick what you see. Pre-set to Don't know.</p>
<p>• <b>{ns} measurement{"s" if ns != 1 else ""}</b> that only the code made, with no judge checking {"them" if ns != 1 else "it"}. Pre-set to Yes; tap No only when one is clearly wrong.</p>
<p><b>Don't know is always safe</b>: that item is simply left out of the Style Bible. When you are done, press Approve and paste the line to the bot.</p></div>
{"<h2>Questions</h2>" if nq else ""}{"".join(c for c in cards if 'class="card q"' in c)}
{"<h2>Measured by the code only</h2>" if ns else ""}{"".join(c for c in cards if 'class="card s"' in c)}
{settled_html}
<p class="skip">Not asked, and left out of the Style Bible (only one judge answered, too minor, or the disagreement would not change anything): {skipped}.</p>
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
    auto = auto_accept(asset_id, workspace)
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
    return {"ok": not auto["errors"], "asset_id": asset_id, "sheet_id": sheet["sheet_id"], "auto_accepted": auto["accepted"], "auto_errors": auto["errors"],
            "questions": q, "statements": len(sheet["items"]) - q,
            "claims_covered": sum(len(i["claim_ids"]) if i["kind"] == "statement" else len(i["claim_ids"]["a"]) + len(i["claim_ids"]["b"]) for i in sheet["items"]),
            "claims_undecided": sheet["claims_undecided"], "not_asked": sheet["not_asked"], "html": str(out / "sheet.html")}


# ------------------------------------------------------------------------------------------ answer
_ANSWER = re.compile(r"^\s*iris-review\s+([A-Za-z0-9_]+)\s+([0-9a-f]{12})\s+([ynsabxz]*)\s*$")


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
    summary: dict[str, int] = {"yes": 0, "no": 0, "chosen": 0, "both": 0, "neither": 0, "skipped": 0}
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
            if code not in "abxzs" or (code == "z" and not it.get("allow_both")):
                raise SheetError(f"{dim}: a question takes a, b, {'z, ' if it.get('allow_both') else ''}x or s, got {code!r}", "usage")
            if code in "ab":
                win, lose = (it["a"], it["b"]) if code == "a" else (it["b"], it["a"])
                kw, kl = ("a", "b") if code == "a" else ("b", "a")
                decisions += [{"claim_id": c, "status": "accepted", "value": None, "reason": f"{tag}: reviewer chose {win} over {lose}"} for c in it["claim_ids"][kw]]
                decisions += [{"claim_id": c, "status": "rejected", "value": None, "reason": f"{tag}: reviewer chose {win} over {lose}"} for c in it["claim_ids"][kl]]
                summary["chosen"] += 1
            elif code == "z":
                decisions += [{"claim_id": c, "status": "accepted", "value": None, "reason": f"{tag}: reviewer sees both {it['a']} and {it['b']}"}
                              for c in it["claim_ids"]["a"] + it["claim_ids"]["b"]]
                summary["both"] += 1
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
