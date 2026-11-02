# Iris studio (Phase 2)

Remotion template that renders vertical reels in the style of the approved Style Bible `archival-motion-v1`
(sha256 `0bc678df…`). Iris (Phase 1) measures the style and checks a finished reel; this folder makes reels.

## What it does

- **Collage with camera moves** (`src/components/Collage.tsx`): each shot is layers (a back plate and cut-outs)
  that the camera moves over with steady Ken Burns speed: pull out, tilt down, pan right or push in, in the
  style's mix. Nearer layers travel further (parallax), cut-outs cast a shadow and drift slightly.
- **Captions** (`src/components/Caption.tsx`): Libre Baskerville, 1-3 words per cue, middle band, in one of the
  references' looks: `label` (black on a yellow label that wipes in, Bethlem), `box` (light italic on a teal
  box that pops, Otis), `plain` / `plain_light` (bare serif, Santos).
- **Transitions** (`src/components/Transition.tsx`): hard cut, RGB-split `glitch` (3 frames) or a short `flash`.
- **Archival grade** (`src/components/Grade.tsx`): `sepia`, `warm_print` or `cool_mono`, slight gate weave and
  flicker, film grain and vignette over everything.
- **Style limits before rendering** (`src/spec.ts`): prohibited moves and over-long shots stop the render;
  cut rate, caption length, first caption time and camera mix outside the Bible print warnings.
  All numbers live in `src/style.ts`.

A reel is a JSON spec (`reels/*.json`): shots (duration, move, transition, layers), caption cues on their own
timeline, and voice-over clips. `reels/sample-calorico.json` is the example.

## Use

```bash
npm install
python3 tools/make_assets.py                 # grain tiles and paper plates into public/gen/
python3 tools/make_sample.py [KIT_DIR]       # sample: voice-over (macOS say), cut-outs, spec
npx remotion render src/index.ts Reel out/raw.mp4 --codec h264 --crf 18 --props=reels/sample-calorico.json
tools/finish.sh out/raw.mp4 out/final.mp4    # loudness -14 LUFS, true peak -1.5 dBTP
```

`npm run studio` opens the Remotion editor. `python3 tools/make_assets.py cutout SRC OUT.png [--mono]` turns any
picture into an archival cut-out.

Then `iris check` the final file against `archival-motion-v1`.

## Measured with Iris (sample, 2026-11-02)

13 shots planned, 11 found (a flash cut and a glitch cut merge with the next shot), cut rate 0.688/s (band
0.625-0.95), no static shot, loudness -14.1 LUFS, true peak -1.5 dBTP, the yellow label read as a solid box.
Strong frame-to-frame flicker or an ease-out camera that moves most at the cut hides the cuts from Iris and
from the eye, so both are kept gentle.

## Known gap

The Bible records ref_7820's caption as olive text with no box; the yellow label in `style.ts` comes from the
style board screenshots. Fix the measurement from that reference's `text.json`.
