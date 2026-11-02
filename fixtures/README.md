# Fixtures

Synthetic clips used by `iris selftest` and the stage tests. They are generated locally with
`tools/make_fixtures.sh` (ffmpeg only) and are not committed; `fixtures/manifest.json` records the
expected frame counts, durations and events for each one so a run can be checked against ground truth.

| Fixture | What it exercises | Expected |
|---|---|---|
| `cfr_30.mp4` | Constant 30 fps, 1080x1920, 6 s, colour bars that change every 2 s | 180 frames, cuts at 2.0 s and 4.0 s |
| `vfr_mixed.mp4` | Variable frame rate (segments at 24, 30 and 60 fps concatenated) | time != frame_id / fps; PTS index must be respected |
| `flash_1frame.mp4` | A single white frame at 3.0 s inside a 6 s clip | the 1-frame event survives detection |
| `duplicate_frames.mp4` | Every 5th frame duplicated (hold) | duplicates preserved, not dropped |
| `rotation_meta.mp4` | 1920x1080 source with `rotate=90` display metadata | display dimensions 1080x1920 |
| `silent.mp4` | Video with no audio stream | audio stage reports `absent`, not failure |
| `truncated.mp4` | The CFR clip cut mid-stream | coverage `partial`, not an exception |
| `caption_1frame.mp4` | A caption visible for exactly one frame (needs `drawtext` or a pre-rendered PNG overlay) | text event candidate retained |

`golden/<name>/golden.json` freezes the facts a correct pipeline must reproduce for one video: frame count, cuts, events, camera classes, light labels, background Lab per shot, caption text, loudness and transcript size, with the OCR and Whisper backends that produced them. `iris selftest --golden` re-analyses each in a throwaway workspace and diffs: labels and counts exactly, numbers within the declared tolerances, caption text by similarity. Facts from a stage whose backend differs are skipped and reported. Goldens are machine-specific: another ffmpeg renders the same fixture with other bytes. The goldens here were frozen on the development Mac; on any other machine run `iris selftest --no-tests --freeze-fixtures` once (after `tools/make_fixtures.sh`) to freeze that machine's own into `<workspace>/golden/` (never committed), which replace these by name. A fixture whose bytes differ from its golden is skipped with that advice, not failed. A real reference is frozen with `iris selftest --no-tests --freeze <asset_id> --name <name>`, also into `<workspace>/golden/`: only its hash and facts are stored, never the media, and the check skips it where the original is not in the workspace.
