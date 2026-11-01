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

Stage extras (`media`, `text`, `audio`, `people`, `interpret`) are installed per milestone; on the Grok Bot VM the lock file pins exact versions.

## Status

Milestone 0 (contracts and environment) in progress. Implemented: `version`, `doctor`, `lexicon`, `selftest`. Every other command exits with code 9 and names its milestone. See `docs/PLAN.es.md` for the full plan and `docs/style_bible.md` for the output contract.

## Non-negotiables

- Code measures; models interpret from a closed vocabulary with abstention. Validation rejects anything else.
- No frame is silently skipped. A corrupt source yields `partial`, not a guess.
- Every claim links to evidence. Every Style Bible links to the review decisions that produced it.
- Secrets live in `secrets/` with mode 600 and are never printed. The VM is shared; treat it as not isolated.
- Everything is English: ids, definitions, prompts, reports, code, bot output.
