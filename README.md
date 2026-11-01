# Iris

Deterministic visual-style analysis of short-form reference videos, interpreted with a closed vocabulary, reviewed by a human, and compressed into a compact, schema-validated **Style Bible** that downstream work follows literally.

Phase 1 only. Nothing here writes scripts, generates footage or edits video.

## What it does

1. **Ingest** a reference from a URL (yt-dlp) or a file. The original never leaves the machine.
2. **Measure every frame** with code: PTS-indexed timeline, per-frame colour and luminance, optical flow in four motion layers, shots and one-frame events, OCR text tracks, per-region colour and light, audio loudness, onsets and transcript. Three coverage axes are reported: decode, measurement, model exposure.
3. **Interpret** only six dimensions with a model, against a closed vocabulary with explicit abstention. Two blind judges: the Grok Bot first (it orchestrates the CLI), then Claude through the API. Disagreement goes to review. A model never writes a number.
4. **Review** in chat. Measured claims are approved in bulk; interpreted ones one by one. Append-only.
5. **Build a Style Bible** from three or more approved references: fifteen blocks, ranges instead of points, a `never` list per block, continuity rules with metric and tolerance, exemplars pointing back to evidence. Under 3 500 tokens.
6. **Check** any new clip against a Style Bible: `pass / warn / fail / not_applicable` per rule and frame.

## Layout

```
iris/        CLI and stages (Python 3.12)
registry/    the vocabulary (single term registry), bindings per target, dictionaries, capabilities snapshots
schemas/     Style Bible JSON Schema and example; claim and interpretation schemas arrive with milestone 3
fixtures/    synthetic clips (generated) and their ground-truth manifest; golden reference later
tools/       fixture generator and maintenance scripts
docs/        planning document (Spanish, the only non-English artifact), Style Bible contract, research
tests/       unit tests
```

Runtime state (`secrets/ db/ artifacts/ refs/ styles/ checks/ ledger/`) lives under `IRIS_WORKSPACE` (default: repo root) and is never committed.

## Quick start (development)

```bash
uv venv --python 3.12 .venv && . .venv/bin/activate
uv pip install -e ".[dev]"
iris doctor
iris selftest
iris lexicon camera.movement.dolly_in
```

Stage extras (`media`, `text`, `audio`, `people`, `interpret`) are installed per milestone. Iris never imports OpenCV; the only cv2 in the venv is `opencv-contrib-python`, pinned by paddlex and mediapipe, and `iris doctor` fails when a second variant is installed.

## Status

Milestone 3 (interpretation and review) implemented: `interpret prepare` writes a packet per asset (windows of ≤8 shots, keyframes at 768 px with hashes, per-shot numeric summaries and code proposals, compact lexicon cards for the model dimensions, the exact evidence ids a judge may cite, and a packet hash); `interpret ingest --judge grok` validates the blind first judge's answer (schema, terms in the registry, cardinality, evidence ids from the packet, packet hash, vocabulary version); `interpret run --provider anthropic` calls Claude (`claude-sonnet-5-5`, structured outputs with a per-window JSON schema, cached system prompt, one repair round, per-reference and monthly budget guards, one ledger line per call with request id, exact model, tokens, cost and image hashes) and refuses to run before the Grok answer exists unless `--skip-grok`; `--provider fixture` replays or synthesises an answer at zero cost. `validate` builds the evidence index (`evidence.json`), code claims (`estimated`: camera movement, light key / side / quality, montage pacing, caption cadence) and model claims (`interpreted`) by fusing the judges (agreement → pending, disagreement → needs_review with a shared group, one abstention → single_judge), keeps claim ids stable across re-runs, preserves review decisions, and reports judge agreement. `claims list`, `review` (single or `--batch`, append-only events with author) and `ledger summary` complete the loop. Observations never become claims. Schemas: `claim.schema.json`, `interpret_answer.schema.json`, each with an example.

Milestone 2 (measurement stages) implemented on top of milestone 1: `analyze` now also runs **shots** (cuts, fades, dissolve candidates, flashes, short inserts, freezes; montage metrics, pHash picture reuse), **motion** (numpy phase-correlation estimator: global translation, divergence, curl, residual, jitter; per-shot class with `apparent_*` labels and alternatives), **text** (PaddleOCR mobile when installed, Tesseract CLI fallback, honest `skipped` otherwise; sampled frames, tracks with one-frame candidates and cue-timing uncertainty), **regions** (coarse automatic skin / subject / graphics / background with coverage; per-region Lab stats and palettes; ΔE2000 versus master and previous shot; light key, side, edge, contrast as `estimated`), **audio** (ebur128 loudness, silences, numpy spectral-flux onsets, cuts-on-onset share, faster-whisper transcript when installed, `absent` when there is no audio stream) and **sheets** (paginated timeline contact sheets, per-shot first/mid/last sheet, palette strip, measurement curves). Each derived stage records `ok | skipped | absent | failed` with a reason in `coverage.json`. Motion, text and audio run concurrently once shots exist; PaddleOCR and faster-whisper run in supervised child processes (`iris/worker.py`) with capped threads and wall-clock budgets, so a stalled frame costs a restart, not the stage, and the two native thread runtimes never share an interpreter. Visually unchanged OCR samples reuse the previous key frame's detections (`frames_reused`).

Milestone 1 (ingest and coverage) implemented: `ingest` (URL via yt-dlp with download limits, direct link, local file; idempotent on content hash), `analyze` (PTS frame index from ffprobe, bounded rawvideo decoding with every presented frame kept, per-frame colour/luminance/sharpness/edge/difference/pHash measurements in numpy, coverage report, idempotent job keys, heavy-job lock, per-stage checkpoints) and `jobs status|resume|cancel|list`. Also `version`, `doctor`, `lexicon`, `selftest`. Everything else exits with code 9 and names its milestone. Per-frame tables are Parquet when pyarrow is installed and gzip-CSV otherwise; `coverage.json` records which. See `docs/PLAN.es.md` and `docs/style_bible.md`.

## Non-negotiables

- Code measures; models interpret from a closed vocabulary with abstention. Validation rejects anything else.
- No frame is silently skipped. A corrupt source yields `partial`, not a guess.
- Every claim links to evidence. Every Style Bible links to the review decisions that produced it.
- Secrets live in `secrets/` with mode 600 and are never printed. The VM is shared; treat it as not isolated.
- Everything is English: ids, definitions, prompts, reports, code, bot output.
