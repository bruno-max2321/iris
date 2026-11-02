"""Stage D: shots, transitions and short events from the per-frame table.

Everything here is derived from measurements already on disk (frames table + PTS index), so it is
cheap, deterministic and re-runnable. Candidates for 1-3 frame events are kept separately and never
suppressed by a minimum shot length. Intervals are half-open in frame ids: [first, last_inclusive + 1)."""

from __future__ import annotations

from typing import Any

import numpy as np

METHOD_VERSION = "shots@0.2.0"

# same-palette cuts (archival sepia, one grade across a collage): the colour histogram barely moves at the
# cut, so the histogram threshold misses it; the picture itself changes (pHash) and the pixel difference
# spikes far above its neighbourhood, and the new picture stays
SP_HIST_MIN = 0.06          # histogram change still well above the in-shot noise
SP_DIFF_MIN = 0.05          # mean absolute pixel difference
SP_DIFF_RATIO = 4.0         # times the median difference of the surrounding frames
SP_DIFF_WINDOW = 12         # frames each side for that median
SP_PHASH_JUMP = 22          # of 64 bits: a different picture
SP_PHASH_STAY = 14          # the new picture three frames later is still the same one
SP_LOOKAHEAD = 3


def _mad(x: np.ndarray) -> float:
    med = np.median(x)
    return float(np.median(np.abs(x - med)) * 1.4826)


def _hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def detect(frames: list[dict[str, Any]], index: dict[str, Any], *, min_shot_frames: int = 2) -> tuple[dict[str, Any], dict[str, Any]]:
    n = len(frames)
    fps = float(index.get("nominal_fps") or 30.0)
    pts = [f.get("pts_time") for f in index["frames"]]
    dur = [f.get("duration_time") for f in index["frames"]]

    def t_of(i: int) -> float | None:
        return pts[i] if i < len(pts) else None

    def t_end(i: int) -> float | None:
        if i >= len(pts) or pts[i] is None:
            return None
        return pts[i] + (dur[i] or (1.0 / fps))

    hist = np.array([(r.get("hist_diff_prev") or 0.0) for r in frames], dtype=float)
    diff = np.array([(r.get("diff_prev") or 0.0) for r in frames], dtype=float)
    L = np.array([r["L_mean"] for r in frames], dtype=float)
    sharp = np.array([r.get("sharpness") or 0.0 for r in frames], dtype=float)

    # --- cut threshold: robust statistics with a floor so static clips do not explode into cuts
    thr = max(0.25, float(np.median(hist[1:]) + 6.0 * _mad(hist[1:]))) if n > 2 else 0.25
    cut_mask = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if hist[i] > thr and hist[i] >= hist[max(1, i - 1)] and hist[i] >= (hist[i + 1] if i + 1 < n else 0):
            cut_mask[i] = True

    phashes = [r.get("phash") for r in frames]

    def ham(a: int, b: int) -> int | None:
        if not (0 <= a < n and 0 <= b < n) or not phashes[a] or not phashes[b]:
            return None
        return _hamming(phashes[a], phashes[b])

    sp_cuts: list[int] = []
    sp_hist = max(SP_HIST_MIN, float(np.median(hist[1:]) + 6.0 * _mad(hist[1:]))) if n > 2 else SP_HIST_MIN
    for i in range(1, n - SP_LOOKAHEAD):
        if cut_mask[i] or hist[i] <= sp_hist or diff[i] <= SP_DIFF_MIN:
            continue
        around = np.concatenate([diff[max(1, i - SP_DIFF_WINDOW):i], diff[i + 1:i + 1 + SP_DIFF_WINDOW]])
        if around.size and diff[i] < SP_DIFF_RATIO * float(np.median(around)):
            continue
        if diff[i] < diff[i - 1] or diff[i] < diff[i + 1]:
            continue
        # the new picture differs from every one of the last frames, so a short insert that returns is no cut
        jump, stay = ham(i - 1, i), ham(i, i + SP_LOOKAHEAD)
        back = [ham(j, i + SP_LOOKAHEAD) for j in range(max(0, i - 1 - SP_LOOKAHEAD), i)]
        if None in (jump, stay) or None in back or jump < SP_PHASH_JUMP or stay > SP_PHASH_STAY or min(back) < SP_PHASH_JUMP:
            continue
        cut_mask[i] = True
        sp_cuts.append(i)

    events: list[dict[str, Any]] = []

    # --- flash: a single frame far from both neighbours in luminance, with two consecutive big changes
    for i in range(1, n - 1):
        if cut_mask[i] and cut_mask[i + 1] and abs(L[i] - L[i - 1]) > 30 and abs(L[i] - L[i + 1]) > 30 \
                and abs(L[i + 1] - L[i - 1]) < 12:
            events.append({"event_id": f"e{len(events):04d}", "type": "flash", "frame_first": i, "frame_last_inclusive": i,
                           "t_in": t_of(i), "t_out": t_end(i), "length_frames": 1, "evidence": {"L_mean": float(L[i]), "L_prev": float(L[i - 1]), "L_next": float(L[i + 1])}})
            cut_mask[i] = False
            cut_mask[i + 1] = False

    # --- short inserts: 2-3 frames between two cuts
    cut_ids = [int(i) for i in np.flatnonzero(cut_mask)]
    for a, b in zip(cut_ids, cut_ids[1:]):
        if 2 <= b - a <= 3:
            events.append({"event_id": f"e{len(events):04d}", "type": "short_insert", "frame_first": a, "frame_last_inclusive": b - 1,
                           "t_in": t_of(a), "t_out": t_of(b), "length_frames": b - a, "evidence": {"hist_diff": [float(hist[a]), float(hist[b])]}})

    # --- freeze: no change for >= 0.5 s
    min_freeze = max(3, int(round(0.5 * fps)))
    run_start = None
    for i in range(1, n + 1):
        still = i < n and diff[i] < 1e-4
        if still and run_start is None:
            run_start = i - 1
        if (not still or i == n) and run_start is not None:
            run_end = i - 1
            if run_end - run_start + 1 >= min_freeze:
                events.append({"event_id": f"e{len(events):04d}", "type": "freeze", "frame_first": run_start, "frame_last_inclusive": run_end,
                               "t_in": t_of(run_start), "t_out": t_end(run_end), "length_frames": run_end - run_start + 1, "evidence": {}})
            run_start = None

    # --- fades to/from black or white: monotonic luminance ramp of >= 6 frames reaching an extreme
    min_fade = 6
    i = 1
    while i < n:
        j = i
        while j + 1 < n and (L[j + 1] - L[j]) * (L[i] - L[i - 1]) > 0 and abs(L[j + 1] - L[j]) > 0.5:
            j += 1
        if j - i + 1 >= min_fade and abs(L[j] - L[i - 1]) > 40 and (L[j] < 6 or L[j] > 94 or L[i - 1] < 6 or L[i - 1] > 94):
            kind = "fade_out" if L[j] < L[i - 1] else "fade_in"
            events.append({"event_id": f"e{len(events):04d}", "type": kind, "frame_first": i - 1, "frame_last_inclusive": j,
                           "t_in": t_of(i - 1), "t_out": t_end(j), "length_frames": j - i + 2, "evidence": {"L_from": float(L[i - 1]), "L_to": float(L[j])}})
            # a fade separates shots at its end (fade out) or start (fade in)
            boundary = j + 1 if kind == "fade_out" else i - 1
            if 0 < boundary < n:
                cut_mask[boundary] = True
            i = j + 1
        else:
            i += 1

    # --- dissolve candidates: sustained medium change without a single spike
    lo, hi = 0.35 * thr, thr
    i = 1
    while i < n:
        if lo < hist[i] < hi and not cut_mask[i]:
            j = i
            while j + 1 < n and lo < hist[j + 1] < hi and not cut_mask[j + 1]:
                j += 1
            if j - i + 1 >= 6 and abs(L[j] - L[i - 1]) > 8:
                mid = (i + j) // 2
                events.append({"event_id": f"e{len(events):04d}", "type": "dissolve_candidate", "frame_first": i, "frame_last_inclusive": j,
                               "t_in": t_of(i), "t_out": t_end(j), "length_frames": j - i + 1, "evidence": {"mean_hist_diff": float(hist[i:j + 1].mean())}})
                cut_mask[mid] = True
            i = j + 1
        else:
            i += 1

    # --- shots from boundaries
    boundaries = [0] + [int(i) for i in np.flatnonzero(cut_mask)] + [n]
    boundaries = sorted(set(boundaries))
    shots: list[dict[str, Any]] = []
    for a, b in zip(boundaries, boundaries[1:]):
        if b - a < min_shot_frames and shots:
            # merge micro-shot into the previous one but keep it as a candidate event
            shots[-1]["frame_last_inclusive"] = b - 1
            continue
        seg = slice(a, b)
        sharpest = a + int(np.argmax(sharp[seg])) if b > a else a
        shots.append({
            "shot_id": f"s{len(shots) + 1:03d}",
            "frame_first": a, "frame_last_inclusive": b - 1,
            "t_in": t_of(a), "t_out": t_end(b - 1),
            "frames": b - a,
            "keyframes": {"first": a, "mid": (a + b - 1) // 2, "last": b - 1, "sharpest": sharpest},
            "L_mean": float(L[seg].mean()), "L_std": float(L[seg].std()),
            "phash_mid": frames[(a + b - 1) // 2].get("phash"),
            "transition_in": "cut" if a > 0 else "start",
        })
    for s in shots:
        s["duration_s"] = (s["t_out"] - s["t_in"]) if (s["t_in"] is not None and s["t_out"] is not None) else s["frames"] / fps
    # label transitions from events
    for e in events:
        for s in shots:
            if e["type"] in ("fade_in", "fade_out", "dissolve_candidate") and s["frame_first"] in (e["frame_last_inclusive"] + 1, e["frame_first"]):
                s["transition_in"] = e["type"]

    total_s = (shots[-1]["t_out"] - shots[0]["t_in"]) if shots and shots[0]["t_in"] is not None and shots[-1]["t_out"] is not None else n / fps
    cuts = [s["frame_first"] for s in shots[1:]]
    cut_times = [t_of(c) for c in cuts if t_of(c) is not None]

    def rate(t0: float, t1: float) -> float | None:
        span = max(1e-6, t1 - t0)
        if t1 <= t0:
            return None
        return round(sum(1 for t in cut_times if t0 <= t < t1) / span, 3)

    lengths = np.array([s["duration_s"] for s in shots], dtype=float) if shots else np.array([0.0])
    hashes = [s["phash_mid"] for s in shots if s.get("phash_mid")]
    clusters: list[str] = []
    reuse = 0
    for h in hashes:
        if any(_hamming(h, c) <= 10 for c in clusters):
            reuse += 1
        else:
            clusters.append(h)

    montage = {
        "duration_s": round(float(total_s), 3),
        "shot_count": len(shots),
        "cut_count": len(cuts),
        "cuts_per_s": {"overall": round(len(cuts) / max(1e-6, total_s), 3),
                        "hook": rate(0.0, min(3.0, total_s)), "body": rate(3.0, max(3.0, total_s - 3.0)), "close": rate(max(0.0, total_s - 3.0), total_s)},
        "shot_length_s": {"min": round(float(lengths.min()), 3), "p25": round(float(np.percentile(lengths, 25)), 3),
                           "p50": round(float(np.percentile(lengths, 50)), 3), "p75": round(float(np.percentile(lengths, 75)), 3),
                           "max": round(float(lengths.max()), 3), "cv": round(float(lengths.std() / max(1e-6, lengths.mean())), 3)},
        "unique_pictures": len(clusters), "picture_reuse_count": reuse,
        "reuse_factor": round(len(hashes) / max(1, len(clusters)), 3),
        "cut_threshold": round(thr, 4), "same_palette_cuts": len(sp_cuts),
    }
    shots_doc = {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "fps_nominal": fps, "frame_count": n,
                 "shots": shots, "montage": montage, "cut_times_s": cut_times}
    events_doc = {"schema_version": "1.0.0", "method_version": METHOD_VERSION, "events": events,
                  "counts": {t: sum(1 for e in events if e["type"] == t) for t in sorted({e["type"] for e in events})}}
    return shots_doc, events_doc
