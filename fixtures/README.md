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

`golden/` holds one real reference whose complete analysis is frozen; `iris selftest --golden` re-runs it and diffs the result.
