# Iris creative vocabulary

This is the description vocabulary used by Iris creativo for analysis claims (`analysis.json`), creative targets (`direction.json`) and the bindings that turn a term into a generation or editing control. Version 1.0.0, generated 2026-11-01. Everything here is in English.

## One description language

There is **one term registry**, `vocabulary.yaml`, and there are **separate binding tables** for each target. They are not two registers with equal weight.

- Camera, light and optics term ids use the canonical Higgsfield guide spelling (`dolly_in`, `pan_left`, `rack_focus`, `whip_pan`, `rim_light`, `contre_jour`, `shallow_depth_of_field`, `match_cut`, `speed_ramp`, ...). Each one cites at least one official Higgsfield page. If none exists, the term is marked `verified: false`.
- Composition uses the 43 original Iris technique ids (`chiaroscuro`, `leadinglines`, `figureground`, ...). Each of these terms carries `iris_technique_id`.
- Opaque Higgsfield preset names (3D Rotation, Lazy Susan, Hero Cam, Buckle Up, ...) are never term ids. They appear only in `bindings/higgsfield-camera-controls.yaml`, mapped by each preset page's definition, not by the English of the label.
- The vocabulary contains no marketing or brand rules. Brand rules belong to the client profile.

## Files

| Path | What it is |
|---|---|
| `vocabulary.yaml` | The term registry: header, measurement-key catalog, 35 dimensions, 260 terms. |
| `vocabulary.schema.json` | JSON Schema (2020-12) for `vocabulary.yaml`. |
| `bindings/higgsfield-cinema-3.5.yaml` | `cinematic_studio_video_3_5`: `light_scheme` and `color_grading` enums, multi-shot, audio, start/end frames. |
| `bindings/higgsfield-cinema-4.0.yaml` | `cinematic_studio_video_4_0`: lighting preset, aperture, lens, camera, pacing and colour palette ids (resolved at runtime). |
| `bindings/higgsfield-cinema-v2.yaml` | `cinematic_studio_video_v2`: the only catalog model with a `speedramp` enum (extra file). |
| `bindings/higgsfield-kling-3.0.yaml` | `kling3_0`, plus `kling_o3_flf` rows for multi-shot. |
| `bindings/higgsfield-kling-4.0.yaml` | `kling4_0`. |
| `bindings/higgsfield-seedance-2.5.yaml` | `seedance_2_5`. |
| `bindings/higgsfield-camera-controls.yaml` | All 65 public Camera Controls presets, each with a term (or null) and a relation. |
| `bindings/effectcraft-0.17.yaml` | EffectCraft MCP tools, engine commands and effects. |
| `bindings/ffmpeg.yaml` | FFmpeg filtergraph snippets. |
| `capabilities/effectcraft-0.17.0-extract.json` | MCP tools, 734 engine commands and 307 effects with parameter ids, extracted from the local EffectCraft reference package. Used by the validator. |
| `capabilities/ffmpeg-8.1-filters.json` | Filters, xfade transitions and curves presets captured from local ffmpeg 8.1. Re-capture this on the Grok Bot VM. |
| `dictionaries/higgsfield-codex-2026-11-01.json` | A copy of the Higgsfield taxonomy (548 entries) with `vocab_term_id` (primary term or null) and `vocab_term_ids` on each entry. |
| `lexicon.md` | Generated cards, one per term and grouped by dimension. |
| `tools/validate_vocabulary.py` | The validator. |
| `tools/build_lexicon.py` | Generates `lexicon.md`, or prints a single card for `iris lexicon <id>`. |
| `capabilities/mcp-higgsfield-video-2026-11-01.json` | Higgsfield MCP video model catalog snapshot (input, not modified). |
| `CHANGELOG.md` | Version history. |

## Term structure

Each dimension declares:

- `temporal_unit`: one of `frame`, `shot`, `sequence` or `video`.
- `cardinality`: `single` (one term per unit, or per region if the dimension is region-scoped) or `multi`.
- `region_scoped`.
- `measurement_keys`: these must be declared in the header catalog, with status `planned` (from the Iris plan) or `proposed` (new here).
- Optional `qualifiers`, for example `speed` for camera.movement, `color` for a fade, `direction` for a wipe.
- Optional `exclusive_groups`.

Each term has:

- `id`, `aliases` and `definition`;
- `observable_cues` (at least one) and `measurement_hints`;
- `counterexamples`: at least one, as `{confused_with, distinguish}`;
- `claim_kind_default`: `measured`, `estimated` or `interpreted`; `designed` is reserved for `direction.json`;
- `sources`: `{url, title, accessed}`;
- `verified`, plus `verification_note` when the term is not verified;
- optionally `region_scope`, `iris_technique_id`, `related_terms`, `prompt_en` (the canonical prompt phrase used by `prompt_only` bindings) and `dictionary_ids`.

A claim refers to a term as `<term_id>` or as the qualified form `<dimension_id>=<term_id>`. Term ids are unique across all dimensions.

### Key distinctions

- **Appearance versus mechanism.**
  - `apparent_push_in` names what is seen.
  - `dolly_in` (camera translation, which produces parallax), `zoom_in` (focal length, with no parallax), `digital_zoom` / `crop_animation` / `punch_in` (post transforms) name how it was made.
  - Use a mechanism term only when the measurements separate the mechanisms. Otherwise use the `apparent_*` term and list the mechanisms as alternatives.
- **Light** is split into four dimensions:
  - `light.direction` (front, side, top, back);
  - `light.quality` (hardness);
  - `light.key` (overall tonal level and contrast);
  - `light.scheme` (named setups such as `contre_jour` and `rim_light`).
- **Colour terms are region-scoped.** Every claim names a region: `background`, `food`, `product`, `skin`, `ui`, `graphics` or `whole_frame`.
- **Motion has four layers:**
  - camera (`camera.movement`);
  - subject (`subject.action`);
  - edit transforms (`edit.transform`);
  - graphics (`graphic.motion`, `typography.*`).

## Bindings

Each row has:

- `term_id`;
- `target`, in one of these forms:
  - `{param, value}`, `{params}` or `media_roles` for Higgsfield;
  - `{command, params}` for EffectCraft;
  - `{filter, filters_used}` for FFmpeg;
  - `{prompt}` for prompt-only rows;
- `relation`: `exact`, `approx`, `prompt_only` or `unsupported`;
- `notes` and `verified_on`.

Each Higgsfield file adds a `prompt_only` row (with the term's `prompt_en`) for every generation-relevant term that no parameter controls. A term that is absent from a file is unsupported on that target.

Some Cinema Studio 4.0 controls are ids that the catalog does not enumerate (`light_id`, `camera_aperture_id`, `camera_lens_id`, `camera_model_id`, `pacing_id`, `color_palette`). Their rows carry `value: null` plus a `value_hint` (the UI label from the official guide), and must be resolved at runtime before submission. Cinema 3.5 `camera_style` values have no published definitions, so no term is bound to them (see `unbound_enums`).

## Usage

The scripts need Python 3.11 (3.9+ also works), `pyyaml` and `jsonschema`.

```bash
python3 -m pip install --user pyyaml jsonschema
python3 tools/validate_vocabulary.py            # full report, exit 0 on success
python3 tools/validate_vocabulary.py --strict   # warnings become errors
python3 tools/build_lexicon.py                  # regenerate lexicon.md
python3 tools/build_lexicon.py --term dolly_in  # one card (what `iris lexicon dolly_in` shows)
```

The validator checks:

- schema validity and unique ids;
- that internal references resolve (counterexamples, related terms, exclusive groups, qualifiers, measurement keys);
- that the 43 Iris techniques are mapped exactly once each;
- region scope;
- official sources on camera, light and optics terms;
- that the term count is within 180–260 and that nothing is in Spanish;
- every binding's `term_id` and `relation`;
- Higgsfield model ids, parameters, enum values and media roles against the MCP catalog;
- the 65 Camera Controls labels against the dictionary;
- EffectCraft tools, commands, effects and parameters against the extract;
- FFmpeg filters, xfade transitions and curves presets against the capture;
- dictionary links.

On the Grok Bot VM, re-capture `capabilities/ffmpeg-8.1-filters.json` with that machine's ffmpeg. The authoring build has no `drawtext` or `subtitles` (no libfreetype or libass); those rows declare `build_requires` and appear as warnings.

## Editing rules

1. Edit `vocabulary.yaml` or `bindings/*.yaml`, then run the validator and `build_lexicon.py`. Never edit `lexicon.md` by hand.
2. Do not add a term without an observable cue, a counterexample and a source. If a fact cannot be verified, set `verified: false` and explain why in `verification_note`.
3. Higgsfield bindings may only use parameters and enum values that exist in the MCP catalog. Refresh the catalog snapshot and re-validate when models change.
4. Never select a Higgsfield enum or preset by the English of its label. Bind it only when an official definition or page supports the mapping.
