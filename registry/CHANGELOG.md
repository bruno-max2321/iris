# Changelog

## 1.0.0 - 2026-11-01

First release of the Iris creative vocabulary.

### Registry
- Added `vocabulary.yaml`, with 35 dimensions and 260 terms:
  - 204 terms verified, 56 marked `verified: false` with a reason;
  - 100 measurement keys: 82 planned in the Iris plan, 18 proposed.
- Camera, light and optics term ids follow the official Higgsfield guide spelling.
- The `composition` dimension carries the 43 Iris technique ids, each linked through `iris_technique_id`.
- Appearance terms (`apparent_push_in`, `apparent_pull_out`, `apparent_lateral_travel`, `apparent_vertical_travel`) are kept separate from mechanism terms (dolly, zoom, crane, arc) and from post transforms (`digital_zoom`, `punch_in`, `crop_animation`).
- Light is split into `light.direction`, `light.quality`, `light.key` and `light.scheme`. Colour dimensions and `material_atmosphere` are region-scoped.
- Added `vocabulary.schema.json` (JSON Schema 2020-12).

### Bindings
- Higgsfield:
  - Cinema Studio 3.5, Cinema Studio 4.0, Cinema Studio v2 (speed ramp), Kling 3.0 (with Kling 3.0 Omni rows), Kling 4.0 and Seedance 2.5, checked against `capabilities/mcp-higgsfield-video-2026-11-01.json`;
  - all 65 public Camera Controls presets, mapped by their page definitions. The four pages that the Codex research could not retrieve (Aerial Pullback, Jib down, Rapid Zoom Out, Timelapse Glam) were read on 2026-11-01.
- EffectCraft 0.17: 70 rows, checked against `capabilities/effectcraft-0.17.0-extract.json`.
- FFmpeg: 44 rows, checked against `capabilities/ffmpeg-8.1-filters.json`.

### Dictionary and tools
- Added `dictionaries/higgsfield-codex-2026-11-01.json`: the Higgsfield taxonomy (548 entries), with `vocab_term_id` and `vocab_term_ids` on each entry.
- Added `tools/validate_vocabulary.py` and `tools/build_lexicon.py`.
- `lexicon.md` is generated from the registry and the bindings.

### Excluded
- Dropped for lack of an official source:
  - `ring_light`, `under_light`, `three_quarter_light` and `softbox`;
  - `hypersaturated` (`saturated` covers it);
  - `setup` and `free_running_music`.
- `soft_side_key` is not a term. The guides only document "soft side light", which is an alias of `side_light` used together with `soft_light`.
