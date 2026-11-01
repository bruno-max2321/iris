# Iris Style Bible — the Phase 1 output contract

Status: specification, 2026-11-01. Nothing here has been produced from a real video yet.

## Decision

Phase 1 ends in **one closed, schema-validated JSON document per style**: `style_bible.json`, validated by `style_bible.schema.json` (JSON Schema 2020-12). A Markdown rendering (`style_bible.md`) is generated from the JSON for human reading and never edited by hand. Every downstream consumer reads the JSON directly and must not read the raw evidence unless it follows an `exemplar` pointer.

Why JSON and not YAML or free text: strict validation with `additionalProperties: false`, native tooling in Python and TypeScript, no implicit typing surprises, and it is what the Iris CLI already emits. Why one document and not several: later phases follow it literally; a single artifact with a hash is the only way to know what they followed.

Why a closed structure: the goal is that a stranger (or a model) given only this document can storyboard, light, color, caption and cut a new video that reads as the same style. Open-ended prose cannot be checked; closed fields with vocabulary ids and numeric ranges can.

## Three layers of Phase 1 output

| Layer | Files | Consumer | Size |
|---|---|---|---|
| 1 Evidence | `manifest.json coverage.json frames.parquet shots.json events.json motion.json text.json color.json audio.json sheets/ windows/ claims.jsonl review_events.jsonl evidence/ report/index.html` | Audit, human review, `iris check`, future training | Unbounded |
| 2 Per-reference analysis | `analysis.json` | Aggregation into styles; point queries | Large |
| 3 **Style Bible** | `styles/<style_id>/style_bible.json` + `.md` | **Every later phase** | **≤ 3 500 tokens** |

Only layer 3 leaves Iris. If a downstream consumer needs more detail, it follows an `exemplar` (`ref`, `shot`, `t`) into layer 1 and loads exactly that interval.

## What the Style Bible contains

Fifteen blocks. Each block carries `meta.claim_kind` (measured / estimated / interpreted / mixed), `meta.review_status` and `meta.n_refs`, so a consumer always knows how much to trust it.

| Block | What it fixes downstream | Primary consumer |
|---|---|---|
| `identity` | One-line recognizability, Iris operations, signature techniques, tone words | Everyone |
| `concept` | The organizing visual idea, recurring metaphors, how each subject class is treated, the viewer promise | Downstream: writing, asset direction |
| `rhythm` | Duration, hook window, cut rate per section, shot length, speech wpm, silence, music relation, image reuse | Downstream: writing, editing |
| `camera` | Movement/shot-size/angle/support distributions, movement dynamics, optics, `never` | Downstream: asset direction; `iris check` |
| `light` | Key, direction, edge softness, contrast ratio, schemes, rim, contact shadows, `never` | Downstream: asset direction; `iris check` |
| `color` | Grade family, per-region Lab ranges and palettes, palette roles, ΔE between shots, `never` | Downstream: asset direction, editing; `iris check` |
| `composition` | Iris techniques by share, subject placement, negative space, depth layers | Downstream: asset direction |
| `environment` | Settings, surfaces, atmosphere, props, clutter | Downstream: asset direction |
| `assets` | Asset families with role, visual spec, runtime share, typical duration, approved reference stills | Downstream: writing, asset direction |
| `typography` | Family class, weights, case, size, placement, lines, entrance, emphasis, caption cadence | Downstream: writing, editing |
| `animation` | Easing, entrance/hold/exit, overshoot, stagger, graphic elements | Downstream: editing |
| `montage` | Transitions, editorial transforms, speed, match logic | Downstream: editing |
| `sound` | Role, loudness, music energy, sfx on cuts, voice treatment | Downstream: editing |
| `narrative` | Ordered structure, beat shares, hook types, text role, CTA treatment | Downstream: writing |
| `continuity_rules` | **Hard rules with metric and tolerance.** What `iris check` enforces on every new clip | `iris check`; every downstream consumer |

Plus `never_global`, `exemplars`, `provenance` and `token_budget`.

## Design rules

1. **Ranges, not points.** Every measured value is a `range` or `quantiles` object. This is what leaves creative freedom inside the style instead of forcing a copy.
2. **Negative space is mandatory.** Every visual block has a `never` list. Prohibitions are the cheapest things to verify and half of a style's identity.
3. **Vocabulary-bound.** Every categorical value is a `term_ref` that must resolve to `vocabulary.yaml`. The validator rejects anything else. No free-text labels for camera, light, color, typography or montage.
4. **Per-region color.** Background, food, product, skin, interface and graphics are measured separately. A green salad and a white interface are never forced to the same histogram.
5. **Traceable.** Every block links to at least one exemplar. `provenance.review_events_sha256` ties the bible to the exact human decisions that produced it.
6. **Budgeted.** `token_budget.limit` is 3 500. The build step measures and fails if exceeded; `rhythm`, `continuity_rules` and `never_*` are never the blocks that get trimmed.
7. **Honest about trust.** Interpreted blocks (`concept`, `narrative`, parts of `identity`) are labeled as such and require `review_status: accepted` before the style can be `approved`.
8. **Aggregated.** `status: approved` requires `built_from` with at least three approved references. One reference gives a `draft`.
9. **Neutral.** No brand, product, platform or marketing angle is hardcoded. Any brand rules are applied downstream on top of the bible, not inside it.
10. **Literal downstream.** Downstream consumers treat `continuity_rules` and `never_*` as law, distributions and ranges as the space they may move in, and `concept` / `narrative` as the brief.

## How it is built

```
iris style build --from ref_a,ref_b,ref_c --style-id <id>
```

1. Load `analysis.json` of each reference; keep only claims with `review_status in {accepted, corrected}`.
2. Aggregate measured fields into ranges/quantiles/distributions across references.
3. Carry interpreted fields only if accepted in at least two of three references (or all, if fewer).
4. Derive `continuity_rules` from the tightest measured ranges (color ΔE, light direction set, caption size, loudness) plus any rule the reviewer added.
5. Pick exemplars by proximity to the median of each block.
6. Validate against the schema, cross-check every `term_ref` against `vocabulary.yaml`, measure tokens, write JSON, render Markdown, hash.

## How we know it is well-posed (milestone 4 tests)

| Test | Procedure | Pass |
|---|---|---|
| Blind reconstruction | A model that sees only the bible describes the video; a reviewer who watched it scores resemblance 0–4 | ≥ 3 |
| Discrimination | Two different styles differ in ≥ 6 of 9 visual blocks; two references of the same style fall inside the bible ranges in ≥ 85 % of measured fields | both |
| Held-out shot prediction | Hide one shot; predict duration, camera movement, key, text presence from the bible; compare with measurement | ≥ 3 of 4 correct |
| Budget | Serialized JSON ≤ 3 500 tokens with the declared tokenizer | pass |
| Traceability | Every block resolves at least one exemplar to evidence | 100 % |
| Round trip | `style_bible.md` regenerated from JSON is byte-identical to the stored one | pass |

## Files in this folder

- `style_bible.schema.json` — the contract.
- `style_bible.example.json` — an illustrative instance with placeholder numbers; not from a real video.
- `README.md` — this file.
