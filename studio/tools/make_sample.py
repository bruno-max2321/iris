"""Build the sample reel spec (reels/sample-calorico.json) and its assets from Calorico's own kit.

    python3 tools/make_sample.py [KIT_DIR]

Voice-over: macOS `say`, one clip per line. Captions: each line split into chunks of at most three words,
timed in proportion to their letters inside the line's clip. Shots: lengths around the style's median,
cut rate inside its band, camera moves in the style's mix, a few glitch and flash transitions.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from make_assets import cutout  # noqa: E402

KIT = Path(sys.argv[1] if len(sys.argv) > 1 else "~/Downloads/Calorico_01_PNG_guia_assets/kit-calorico").expanduser() / "assets"
GEN = ROOT / "public" / "gen"
VOICE = "Daniel"
LINES = [
    ["It started", "with one photo."],
    ["A plate", "of octopus,"],
    ["and one question:"],
    ["how many calories?"],
    ["Calorico", "looked closer,"],
    ["counted", "every ingredient,"],
    ["and wrote", "it down."],
    ["Every meal,"],
    ["one photo."],
    ["That's Calorico."],
]
LEAD_S, GAP_S, TAIL_S = 0.15, 0.22, 0.7


def sh(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def voice() -> tuple[list[dict], list[dict], float]:
    cues, audio, t = [], [], LEAD_S
    for k, chunks in enumerate(LINES):
        line = " ".join(chunks)
        aiff, wav = GEN / f"vo_{k:02d}.aiff", GEN / f"vo_{k:02d}.wav"
        sh("say", "-v", VOICE, "-r", "185", "-o", str(aiff), line)
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "48000", "-ac", "1", str(wav))
        aiff.unlink()
        dur = float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)))
        audio.append({"src": f"gen/{wav.name}", "atS": round(t, 3)})
        letters = sum(len(c) for c in chunks)
        at = t
        for c in chunks:
            hold = max(0.3, dur * len(c) / letters)
            cues.append({"text": c, "atS": round(at, 3), "holdS": round(hold, 3)})
            at += hold
        t += dur + GAP_S
    return cues, audio, t - GAP_S + TAIL_S


def pictures() -> dict[str, str]:
    food = Image.open(KIT / "ui-crop-2.png").convert("RGB")
    srcs = {
        "food": food.crop((40, 70, 560, 470)),
        "food_close": food.crop((160, 100, 460, 400)),
        "counter": Image.open(KIT / "ui-crop-1.png").convert("RGB"),
        "detail": Image.open(KIT / "ui-crop-3.png").convert("RGB"),
        "icon": Image.open(KIT / "calorico-icon.webp").convert("RGB"),
    }
    for i in (1, 2, 3, 4):
        im = Image.open(KIT / f"calorico-screen-{i}.webp").convert("RGB")
        srcs[f"screen{i}"] = im.crop((0, int(im.height * 0.19), im.width, im.height))
    out = {}
    for name, im in srcs.items():
        tmp = GEN / f"_{name}.png"
        im.save(tmp)
        cutout(tmp, GEN / f"cut_{name}.png")
        tmp.unlink()
        out[name] = f"gen/cut_{name}.png"
    return out


def plate(name: str, w: float = 1.42) -> dict:
    return {"src": f"gen/{name}.jpg", "x": 0.5, "y": 0.5, "w": w, "depth": 0}


def cut(p: str, x: float, y: float, w: float, rot: float, depth: float = 1) -> dict:
    return {"src": p, "x": x, "y": y, "w": w, "rotate": rot, "depth": depth, "shadow": True}


def main() -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    cues, audio, total = voice()
    P = pictures()
    # (seconds, move, transition, layers); the last shot takes what is left of the voice-over
    plan = [
        (1.5, "pull_out", "cut", [plate("paper_cream"), cut(P["food"], 0.5, 0.47, 0.92, -3)]),
        (0.7, "tilt_down", "glitch", [plate("paper_cream"), cut(P["food_close"], 0.5, 0.5, 1.05, 2)]),
        (1.1, "pull_out", "cut", [plate("paper_grey"), cut(P["screen2"], 0.52, 0.5, 0.66, 4), cut(P["food"], 0.25, 0.22, 0.38, -8, 0.6)]),
        (1.3, "pan_right", "cut", [plate("paper_cream"), cut(P["food"], 0.3, 0.36, 0.5, -5, 0.5), cut(P["food_close"], 0.68, 0.62, 0.52, 6)]),
        (0.8, "pull_out", "flash", [plate("paper_cream"), cut(P["screen3"], 0.5, 0.5, 0.7, -3)]),
        (1.2, "tilt_down", "cut", [plate("paper_grey"), cut(P["counter"], 0.48, 0.52, 0.78, 3)]),
        (1.0, "pull_out", "glitch", [plate("paper_cream"), cut(P["detail"], 0.52, 0.5, 0.8, -4)]),
        (1.8, "push_in", "cut", [plate("paper_dark"), cut(P["screen4"], 0.5, 0.5, 0.66, 2), cut(P["screen1"], 0.2, 0.78, 0.36, -10, 0.5)]),
        (0.7, "pull_out", "cut", [plate("paper_cream"), cut(P["food"], 0.5, 0.42, 0.9, 4), cut(P["food_close"], 0.72, 0.74, 0.42, -7, 1.3)]),
        (1.1, "tilt_down", "cut", [plate("paper_grey"), cut(P["screen1"], 0.5, 0.5, 0.72, -2)]),
        (1.2, "pull_out", "glitch", [plate("paper_cream"), cut(P["food_close"], 0.36, 0.4, 0.6, -6, 0.6), cut(P["screen2"], 0.66, 0.6, 0.5, 5)]),
        (0.9, "pan_right", "cut", [plate("paper_cream"), cut(P["counter"], 0.5, 0.5, 0.82, 2)]),
    ]
    used = sum(p[0] for p in plan)
    plan.append((round(total - used, 3), "pull_out", "flash", [plate("paper_cream"), cut(P["icon"], 0.5, 0.45, 0.56, 0)]))
    spec = {
        "title": "Calorico: one photo (archival-motion-v1 sample)",
        "grade": "sepia", "look": "label", "background": "#E2D4B8",
        "shots": [{"durationS": d, "move": m, "transitionIn": tr, "layers": ly} for d, m, tr, ly in plan],
        "cues": cues, "audio": audio,
    }
    (ROOT / "reels" / "sample-calorico.json").write_text(json.dumps(spec, indent=1))
    print(f"{len(plan)} shots, {total:.2f} s, cut rate {(len(plan) - 1) / total:.3f}/s, {len(cues)} cues")


if __name__ == "__main__":
    main()
