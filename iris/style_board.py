"""Style board: the visual side of a Style Bible.

The bible JSON says what the style is in numbers and terms; the board shows it. For every reference it
picks the frames that carry the most style information and saves them as screenshots:

- opening: the first three shots (what the viewer sees before deciding to stay);
- color: the shot whose master-region colour is closest to the style's typical colour;
- light: the shot whose contrast is closest to the style's median contrast;
- captions: a caption cue of typical length, at the moment its full text is on screen;
- camera: the shot with the strongest accepted claim of the style's dominant movement (first, mid, last);
- transitions: the first fade or dissolve (outgoing frame, incoming frame);
- screen time: the longest shots, which define the look by sheer duration.

Shot frames use the shot's sharpest keyframe. Frames named in the bible's `exemplars` are badged.
Screenshots go to styles/<style_id>/visual/ (JPEG, long side FRAME_LONG_SIDE), the selection with its
reasons to visual/board.json (for the generator in later phases) and a self-contained
styles/<style_id>/style_board.html for people. Nothing here changes the bible or its hash. When a
downloaded original was removed by gc, shot frames fall back to its saved evidence frames."""

from __future__ import annotations

import base64
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from . import continuity, ingest

METHOD_VERSION = "style_board@0.1.0"
FRAME_LONG_SIDE = 720
OPENING_SHOTS = 3
LONGEST_SHOTS = 4
SECTIONS = [
    ("opening", "Opening", "The first shots of each reference: what the viewer sees before deciding to stay."),
    ("color", "Colour", "The shot closest to the style's typical colour in each reference."),
    ("light", "Light", "The shot closest to the style's median contrast in each reference."),
    ("captions", "Captions", "A caption cue of typical length, captured when its full text is on screen."),
    ("camera", "Camera", "The clearest example of the style's dominant camera movement: first, middle and last frame."),
    ("transitions", "Transitions", "The first soft transition: the outgoing frame, then the incoming one."),
    ("screen_time", "Screen time", "The longest shots: they define the look by sheer duration."),
]
FADES = ("fade_in", "fade_out", "dissolve_candidate")


def _e(x: Any) -> str:
    return html.escape(str(x), quote=True)


def _shots(docs: dict[str, Any]) -> list[dict[str, Any]]:
    return (docs.get("shots") or {}).get("shots") or []


def _key(shot: dict[str, Any], which: str = "sharpest") -> int:
    k = shot.get("keyframes") or {}
    v = k.get(which, k.get("mid", shot["frame_first"]))
    return int(v)


def _pick(rd: dict[str, Any], shot: dict[str, Any], frame: int, why: str) -> dict[str, Any]:
    fps = rd["fps"]
    return {"ref": rd["asset_id"], "shot": shot["shot_id"], "frame": int(frame), "t_s": round(int(frame) / fps, 2), "why": why}


def _shot_of(rd: dict[str, Any], frame: int) -> dict[str, Any]:
    shots = _shots(rd["docs"])
    return next((s for s in shots if s["frame_first"] <= frame <= s["frame_last_inclusive"]), shots[0])


def _dominant_movement(bible: dict[str, Any]) -> str | None:
    mv = (bible.get("camera") or {}).get("movement")
    return max(mv.items(), key=lambda kv: kv[1])[0] if isinstance(mv, dict) and mv else None


def _master_region(bible: dict[str, Any]) -> str | None:
    regions = (bible.get("color") or {}).get("regions") or {}
    return "background" if "background" in regions else ("frame" if "frame" in regions else None)


def select(bible: dict[str, Any], refs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """section -> picks, deterministic for the same bible and stage outputs."""
    out: dict[str, list[dict[str, Any]]] = {name: [] for name, _, _ in SECTIONS}
    region = _master_region(bible)
    contrasts = [c["light"]["contrast_ratio_p95_p5"] for rd in refs for c in (rd["docs"].get("color") or {}).get("shots", [])
                 if c.get("status") == "ok" and (c.get("light") or {}).get("contrast_ratio_p95_p5") is not None]
    cr_med = float(np.median(contrasts)) if contrasts else None
    blocks_all = [(rd, b) for rd in refs for b in continuity.caption_blocks(rd["docs"]) or []]
    words_med = float(np.median([b.get("words") or 0 for _, b in blocks_all])) if blocks_all else None
    movement = _dominant_movement(bible)
    from .style import _claim_weight
    for rd in refs:
        shots = _shots(rd["docs"])
        if not shots:
            continue
        by_id = {s["shot_id"]: s for s in shots}
        for k, s in enumerate(shots[:OPENING_SHOTS]):
            out["opening"].append(_pick(rd, s, _key(s), f"opening shot {k + 1}, {float(s['t_in']):.2f}-{float(s['t_out']):.2f} s"))
        if region:
            units = [u for u in continuity.units_delta_e(rd["docs"], {"region": region}, bible) or [] if u.get("shot_id") in by_id]
            if units:
                u = min(units, key=lambda x: (x["value"], x["shot_id"]))
                s = by_id[u["shot_id"]]
                out["color"].append(_pick(rd, s, _key(s), f"{region} colour {u['value']:g} dE00 from the style's typical"))
        if cr_med is not None:
            items = [c for c in (rd["docs"].get("color") or {}).get("shots", []) if c.get("status") == "ok" and c["shot_id"] in by_id
                     and (c.get("light") or {}).get("contrast_ratio_p95_p5") is not None]
            if items:
                c = min(items, key=lambda x: (abs(x["light"]["contrast_ratio_p95_p5"] - cr_med), x["shot_id"]))
                s = by_id[c["shot_id"]]
                light = c.get("light") or {}
                desc = ", ".join(str(light[k]) for k in ("key", "side", "edge") if light.get(k))
                out["light"].append(_pick(rd, s, _key(s), f"contrast {light['contrast_ratio_p95_p5']:g} (style median {cr_med:.3g})" + (f"; {desc}" if desc else "")))
        blocks = continuity.caption_blocks(rd["docs"]) or []
        if blocks and words_med is not None:
            b = min(blocks, key=lambda x: (abs((x.get("words") or 0) - words_med), -(x.get("lines") or 1), x["frame_first_seen"]))
            tracks = {t["track_id"]: t for t in (rd["docs"].get("text") or {}).get("tracks") or []}
            full = [tracks[i].get("frame_full_text_seen") for i in b.get("track_ids") or [] if i in tracks and tracks[i].get("frame_full_text_seen") is not None]
            f0, f1 = int(b["frame_first_seen"]), int(b["frame_last_seen"])
            frame = min(max(max(full) if full else (f0 + f1) // 2, f0), f1)
            text = (b.get("text") or "").strip()
            out["captions"].append(_pick(rd, _shot_of(rd, frame), frame, f"“{text[:80]}”, {b.get('words')} words on {b.get('lines', 1)} line(s)"))
        if movement:
            cl = [c for c in rd["decided"] if c["eff_dimension"] == "camera.movement" and c["eff_term"] == movement and c.get("unit_id") in by_id]
            if cl:
                c = max(cl, key=lambda x: (_claim_weight(x), x["claim_id"]))
                s = by_id[c["unit_id"]]
                for which in ("first", "mid", "last"):
                    out["camera"].append(_pick(rd, s, _key(s, which), f"{movement.replace('_', ' ')} ({c['review_status']}), {which} frame"))
        for k, s in enumerate(shots):
            if s.get("transition_in") in FADES and k > 0:
                prev = shots[k - 1]
                out["transitions"].append(_pick(rd, prev, _key(prev, "last"), f"before the {s['transition_in'].replace('_', ' ')}"))
                out["transitions"].append(_pick(rd, s, _key(s, "mid"), f"after the {s['transition_in'].replace('_', ' ')}"))
                break
        longest = sorted(shots, key=lambda s: (-float(s.get("duration_s") or 0.0), s["shot_id"]))[:LONGEST_SHOTS]
        for s in sorted(longest, key=lambda s: s["frame_first"]):
            out["screen_time"].append(_pick(rd, s, _key(s), f"{float(s.get('duration_s') or 0.0):.2f} s on screen"))
    named: dict[tuple[str, str], list[str]] = {}
    for kind, lst in (bible.get("exemplars") or {}).items():
        for e in lst:
            named.setdefault((e["ref"], e["shot"]), []).append(kind)
    for picks in out.values():
        for p in picks:
            if (p["ref"], p["shot"]) in named:
                p["bible_exemplar"] = sorted(named[(p["ref"], p["shot"])])
    return {k: v for k, v in out.items() if v}


def _file(p: dict[str, Any]) -> str:
    return f"{p['ref']}_{p['frame']:06d}.jpg"


def _materialize(rd: dict[str, Any], frames: set[int], vis: Path) -> list[int]:
    """Write the missing screenshots of one reference; returns the frames that could not be produced."""
    from PIL import Image

    todo = sorted(f for f in frames if not (vis / f"{rd['asset_id']}_{f:06d}.jpg").exists())
    if not todo:
        return []
    m = ingest.load_manifest(rd["asset_id"], rd["dir"].parent.parent)
    try:
        src = ingest.source_path(m)
    except ingest.IngestError:
        src = None
    if src is not None:
        from . import decode

        vid = (m.get("probe") or {}).get("video") or {}
        dw, dh = int(vid.get("display_width") or 0), int(vid.get("display_height") or 0)
        scale = min(1.0, FRAME_LONG_SIDE / max(dw, dh, 1))
        w, h = max(2, int(dw * scale) // 2 * 2), max(2, int(dh * scale) // 2 * 2)
        for fid, rgb in decode.pick_frames_iter(src, todo, w, h):
            Image.fromarray(rgb).save(vis / f"{rd['asset_id']}_{fid:06d}.jpg", "JPEG", quality=85)
    else:  # the original is gone: use the evidence frames gc saved (shot keyframes only)
        saved = {}
        for s in _shots(rd["docs"]):
            for which, fid in (s.get("keyframes") or {}).items():
                p = rd["dir"] / "evidence_frames" / f"keyframe_{s['shot_id']}_{which}.jpg"
                if p.exists():
                    saved.setdefault(int(fid), p)
        for fid in todo:
            if fid in saved:
                Image.open(saved[fid]).convert("RGB").save(vis / f"{rd['asset_id']}_{fid:06d}.jpg", "JPEG", quality=85)
    return [f for f in todo if not (vis / f"{rd['asset_id']}_{f:06d}.jpg").exists()]


def _summary(bible: dict[str, Any], section: str) -> list[str]:
    from .style import _fmt

    def get(*path: str) -> Any:
        cur: Any = bible
        for k in path:
            cur = cur.get(k) if isinstance(cur, dict) else None
        return cur

    def line(label: str, v: Any) -> str | None:
        if v in (None, "", [], {}):
            return None
        s = _fmt(v) if isinstance(v, (dict, list, bool, float)) else str(v)
        return f"{label}: {s}" if s else None

    rows: list[str | None] = []
    if section == "opening":
        rows = [line("hook cut rate", get("rhythm", "cut_rate_per_s", "hook")), line("first text at", get("rhythm", "hook", "first_text_at_s")),
                line("hook type", get("narrative", "hook_type"))]
    elif section == "color":
        rows = [line("grade", get("color", "grade_family")), line("temperature", get("color", "temperature")),
                line("shot-to-shot colour drift", get("color", "delta_e_between_shots"))]
    elif section == "light":
        rows = [line("key", get("light", "key")), line("edge", get("light", "edge")), line("direction", get("light", "direction")),
                line("contrast", get("light", "contrast_ratio"))]
    elif section == "captions":
        rows = [line("family", get("typography", "family_class")), line("case", get("typography", "case")),
                line("size (share of frame height)", get("typography", "size_rel_frame_h")), line("placement", get("typography", "placement")),
                line("cadence", get("typography", "caption_cadence")), line("hold", get("animation", "hold_ms"))]
    elif section == "camera":
        rows = [line("movement", get("camera", "movement")), line("shot size", get("camera", "shot_size"))]
    elif section == "transitions":
        rows = [line("transitions", get("montage", "transitions"))]
    elif section == "screen_time":
        rows = [line("shot length", get("rhythm", "shot_length_s")), line("cut rate", get("rhythm", "cut_rate_per_s", "overall"))]
    return [r for r in rows if r]


def _swatches(bible: dict[str, Any]) -> str:
    out = []
    for name, reg in ((bible.get("color") or {}).get("regions") or {}).items():
        pal = reg.get("palette") or []
        if pal:
            out.append(f'<span class="pal"><b>{_e(name)}</b> ' + "".join(f'<i class="sw" style="background:{_e(h)}" title="{_e(h)}"></i>' for h in pal) + "</span>")
    return "".join(out)


def render(bible: dict[str, Any], picks: dict[str, list[dict[str, Any]]], vis: Path) -> str:
    sid = bible["style_id"]
    ident = (bible.get("identity") or {}).get("one_line")
    parts = []
    for name, title, blurb in SECTIONS:
        lst = picks.get(name)
        if not lst:
            continue
        summ = _summary(bible, name)
        figs = []
        for p in lst:
            f = vis / _file(p)
            if not f.exists():
                continue
            img = "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode("ascii")
            badge = "".join(f'<span class="badge">bible: {_e(k)}</span>' for k in p.get("bible_exemplar") or [])
            figs.append(f'<figure><img src="{img}" alt="{_e(p["ref"])} {_e(p["shot"])} frame {p["frame"]}" loading="lazy">'
                        f'<figcaption><span class="rid">{_e(p["ref"])}</span><br><b>{_e(p["shot"])}</b> · {p["t_s"]:.2f} s · frame {p["frame"]}{badge}'
                        f'<br>{_e(p["why"])}</figcaption></figure>')
        rows = [f'<div class="grid">{"".join(figs)}</div>'] if figs else []
        if not rows:
            continue
        extra = f'<div class="pals">{_swatches(bible)}</div>' if name == "color" else ""
        rules = "".join(f"<li>{_e(s)}</li>" for s in summ)
        parts.append(f'<section id="{name}"><h2>{_e(title)}</h2><p class="sub">{_e(blurb)}</p>'
                     + (f'<ul class="rules">{rules}</ul>' if rules else "") + extra + "".join(rows) + "</section>")
    nav = " · ".join(f'<a href="#{n}">{_e(t)}</a>' for n, t, _ in SECTIONS if picks.get(n))
    crs = "".join(f"<li><code>{_e(r['rule_id'])}</code> {_e(r['metric'])} {_e(r['tolerance'])} <span class=\"sub\">({_e(r['severity'])})</span></li>"
                  for r in bible.get("continuity_rules") or [])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Style board {_e(sid)}</title><style>
:root{{--bg:#fafaf8;--fg:#1d1d1b;--mute:#6b6b66;--line:#e2e1dc;--card:#fff;--accent:#3b5bdb}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#ecebe6;--mute:#9a9992;--line:#2c2c2a;--card:#1e1e1c;--accent:#91a7ff}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,sans-serif}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px 64px}}h1{{margin:0 0 4px;font-size:24px}}h2{{margin:40px 0 4px;font-size:19px}}
.sub{{color:var(--mute);font-size:13px;margin:0 0 8px}}nav{{margin:12px 0 0;font-size:14px}}a{{color:var(--accent)}}
.rules{{margin:6px 0 12px;padding-left:18px;font-size:14px}}.rid{{font-size:11px;font-family:ui-monospace,monospace}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin:10px 0}}figure{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden}}
img{{width:100%;display:block;background:#000}}figcaption{{font-size:12px;padding:6px 8px;color:var(--mute)}}figcaption b{{color:var(--fg)}}
.badge{{display:inline-block;margin-left:6px;padding:0 6px;border-radius:9px;background:var(--accent);color:var(--bg);font-size:11px}}
.pals{{margin:4px 0 10px}}.pal{{display:inline-block;margin-right:16px;font-size:13px}}.sw{{display:inline-block;width:22px;height:22px;border-radius:4px;margin-left:3px;vertical-align:middle;border:1px solid var(--line)}}
code{{font-size:12px}}</style></head><body><main>
<h1>Style board · {_e(sid)}</h1>
<p class="sub">Style Bible {_e(bible.get("status"))} · built from {len(bible.get("built_from") or [])} reference(s): {_e(", ".join(bible.get("built_from") or []))} · {_e(METHOD_VERSION)}</p>
{f'<p>{_e(ident)}</p>' if ident else ''}
<p class="sub">Screenshots chosen by measurement: each one is the frame of a reference that best shows one part of the style. The numbers and rules live in style_bible.json; this page only shows them.</p>
<nav>{nav}{' · <a href="#rules">Continuity rules</a>' if crs else ''}</nav>
{"".join(parts)}
{f'<section id="rules"><h2>Continuity rules</h2><ul class="rules">{crs}</ul></section>' if crs else ''}
</main></body></html>
"""


def build(style_id: str, workspace: Path | None = None) -> dict[str, Any]:
    from . import style

    ws = style._ws(workspace)
    d = style.style_dir(style_id, ws)
    bible = style.load_bible(style_id, ws)
    refs = [style.load_reference(aid, ws) for aid in bible.get("built_from") or []]
    picks = select(bible, refs)
    vis = d / "visual"
    vis.mkdir(parents=True, exist_ok=True)
    missing = {}
    for rd in refs:
        frames = {p["frame"] for lst in picks.values() for p in lst if p["ref"] == rd["asset_id"]}
        lost = _materialize(rd, frames, vis)
        if lost:
            missing[rd["asset_id"]] = lost
    for lst in picks.values():
        for p in lst:
            p["file"] = f"visual/{_file(p)}" if (vis / _file(p)).exists() else None
    doc = {"style_id": style_id, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "method_version": METHOD_VERSION,
           "bible_sha256": (d / "style_bible.sha256").read_text(encoding="utf-8").strip() if (d / "style_bible.sha256").exists() else None,
           "sections": picks}
    (vis / "board.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    out = d / "style_board.html"
    out.write_text(render(bible, picks, vis), encoding="utf-8")
    n = sum(1 for lst in picks.values() for p in lst if p["file"])
    return {"ok": n > 0, "path": str(out), "index": str(vis / "board.json"), "screenshots": n,
            "sections": {k: len(v) for k, v in picks.items()}, "missing_frames": missing}
