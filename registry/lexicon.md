# Iris lexicon

Generated from `vocabulary.yaml` v1.0.0 (2026-11-01) by `tools/build_lexicon.py`. Do not edit by hand.
38 dimensions, 279 terms. Look up one card with `iris lexicon <term_id>` or `python3 tools/build_lexicon.py --term <term_id>`.

## Dimensions

- [camera.movement](#dim-camera-movement) (shot, multi, 24 terms)
- [camera.shot_size](#dim-camera-shot_size) (shot, single, 7 terms)
- [camera.angle](#dim-camera-angle) (shot, multi, 7 terms)
- [camera.support](#dim-camera-support) (shot, single, 7 terms)
- [subject.action](#dim-subject-action) (shot, multi, 3 terms)
- [optics](#dim-optics) (shot, multi, 11 terms)
- [light.direction](#dim-light-direction) (shot, single, 4 terms)
- [light.quality](#dim-light-quality) (shot, single, 3 terms)
- [light.key](#dim-light-key) (shot, single, 3 terms)
- [light.scheme](#dim-light-scheme) (shot, multi, 7 terms)
- [color.grade_family](#dim-color-grade_family) (shot, single, 8 terms)
- [color.palette_role](#dim-color-palette_role) (shot, multi, 3 terms)
- [color.temperature](#dim-color-temperature) (shot, single, 4 terms)
- [color.saturation_level](#dim-color-saturation_level) (shot, single, 3 terms)
- [color.contrast_level](#dim-color-contrast_level) (shot, multi, 5 terms)
- [framing.placement](#dim-framing-placement) (frame, multi, 4 terms)
- [composition](#dim-composition) (frame, multi, 43 terms)
- [montage.transition](#dim-montage-transition) (sequence, single, 9 terms)
- [montage.pacing](#dim-montage-pacing) (video, single, 4 terms)
- [montage.speed](#dim-montage-speed) (shot, single, 6 terms)
- [edit.transform](#dim-edit-transform) (shot, multi, 7 terms)
- [graphic.motion](#dim-graphic-motion) (shot, multi, 11 terms)
- [typography.family_class](#dim-typography-family_class) (shot, single, 7 terms)
- [typography.weight](#dim-typography-weight) (shot, single, 3 terms)
- [typography.case](#dim-typography-case) (shot, single, 4 terms)
- [typography.entrance](#dim-typography-entrance) (shot, single, 5 terms)
- [typography.emphasis](#dim-typography-emphasis) (shot, multi, 5 terms)
- [typography.placement](#dim-typography-placement) (shot, single, 4 terms)
- [caption.cadence](#dim-caption-cadence) (sequence, single, 3 terms)
- [sound.role](#dim-sound-role) (video, multi, 6 terms)
- [sound.music_relation](#dim-sound-music_relation) (sequence, multi, 4 terms)
- [narrative.function](#dim-narrative-function) (shot, multi, 9 terms)
- [material_atmosphere](#dim-material_atmosphere) (shot, multi, 8 terms)
- [defect](#dim-defect) (shot, multi, 18 terms)
- [style.medium](#dim-style-medium) (shot, single, 4 terms)
- [light.side](#dim-light-side) (shot, single, 4 terms)
- [material.surface](#dim-material-surface) (shot, multi, 7 terms)
- [narrative.hook_type](#dim-narrative-hook_type) (sequence, multi, 5 terms)

<a id="dim-camera-movement"></a>
## camera.movement

Temporal unit `shot`, cardinality `multi`.

Apparent or mechanical movement of the camera viewpoint during a shot (layer 1 of the four motion layers). Mechanism terms (dolly_*, zoom_*, crane_*, arc_*, pan_*, tilt_*) require evidence that separates translation from rotation from focal-length change; when the evidence cannot separate them, use the apparent_* terms and list the mechanisms as alternatives in the claim. Editorial transforms (digital zoom, crop animation, added shake) belong to edit.transform, subject motion to subject.action.

- Qualifier `speed`: slow, medium, fast. Perceived speed of the move, backed by motion.velocity_profile.

Measurement keys: `motion.flow_magnitude`, `motion.flow_direction`, `motion.flow_divergence`, `motion.flow_curl`, `motion.flow_jitter`, `motion.parallax_ratio`, `motion.global_affine`, `motion.subject_track`, `motion.subject_vs_background`, `motion.velocity_profile`, `motion.motion_blur_streak`

<a id="static"></a>
### static

dimension `camera.movement` | unit `shot` | claim `measured` | verified

The viewpoint and framing stay fixed for the shot; only the subject or the light changes.

**Aliases:** locked-off; Static; fixed camera; tripod fixed

**Observable cues**
- Background features keep the same pixel position across the shot
- No global flow beyond noise level

**Measurement hints**
- Global flow magnitude near zero after excluding subject regions; motion.global_affine translation, scale and rotation ~0
- Low motion.flow_jitter (otherwise consider handheld)

**Not to be confused with**
- [`handheld`](#handheld): Handheld shows small irregular global motion (jitter) even when the operator tries to hold still.
- [`freeze_frame`](#freeze_frame): A freeze also stops the subject; static keeps subject motion and sensor noise alive.

**Related:** typically_realized_by [`locked_off`](#locked_off)

**Prompt phrase:** "The camera stays completely still, locked off on a tripod."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Static'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0070, HF-0456

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Static](https://higgsfield.ai/motion/c43e6d97-a55a-45d7-b5bc-b3a55d3a6e8e) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="pan_left"></a>
### pan_left

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera rotates horizontally toward screen-left around its own position.

**Aliases:** Pan Left; pan left

**Observable cues**
- The whole scene slides toward screen-right at roughly uniform speed regardless of depth
- Vertical lines stay vertical; no change in relative overlap between near and far objects

**Measurement hints**
- Global horizontal flow pointing right (+x) with low motion.parallax_ratio (near and far layers move together)
- motion.global_affine dominated by +tx; divergence ~0

**Not to be confused with**
- [`dolly_left`](#dolly_left): A lateral dolly (truck) produces depth-dependent parallax: near objects move faster than far ones.
- [`crop_animation`](#crop_animation): A crop animation over a still frame has zero parallax and no perspective or motion-blur change; check for upscale softness.

**Prompt phrase:** "The camera pans slowly to the left from a fixed position."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Pan Left'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0064, HF-0449

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Pan Left](https://higgsfield.ai/motion/6f087874-24f3-4d48-9eb9-f4349ac6a105) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="pan_right"></a>
### pan_right

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera rotates horizontally toward screen-right around its own position.

**Aliases:** Pan Right; pan right

**Observable cues**
- The whole scene slides toward screen-left at roughly uniform speed regardless of depth

**Measurement hints**
- Global horizontal flow pointing left (-x) with low motion.parallax_ratio
- motion.global_affine dominated by -tx; divergence ~0

**Not to be confused with**
- [`dolly_right`](#dolly_right): A lateral dolly shows depth-dependent parallax; a pan does not.
- [`crop_animation`](#crop_animation): A crop animation over a still frame has zero parallax and no perspective change.

**Prompt phrase:** "The camera pans slowly to the right from a fixed position."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Pan Right'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0064, HF-0450

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Pan Right](https://higgsfield.ai/motion/ce0b3d96-be4c-4b2d-962a-340dd386d910) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="tilt_up"></a>
### tilt_up

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera rotates vertically upward around its own position.

**Aliases:** Tilt up; tilt up

**Observable cues**
- The scene slides downward in frame; the horizon moves down
- Vertical lines may converge slightly more toward the top

**Measurement hints**
- Global vertical flow pointing down (+y) with low motion.parallax_ratio

**Not to be confused with**
- [`crane_up`](#crane_up): A crane rise translates the camera: foreground and background shift by different amounts (parallax).
- [`crop_animation`](#crop_animation): A vertical crop animation over a still frame keeps perspective constant.

**Prompt phrase:** "The camera tilts up slowly from a fixed position."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Tilt up'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0065, HF-0462

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Tilt up](https://higgsfield.ai/motion/9f127dad-0db0-4e3d-a440-3cfbffca30b6) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="tilt_down"></a>
### tilt_down

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera rotates vertically downward around its own position.

**Aliases:** Tilt Down; tilt down

**Observable cues**
- The scene slides upward in frame; the horizon moves up

**Measurement hints**
- Global vertical flow pointing up (-y) with low motion.parallax_ratio

**Not to be confused with**
- [`crane_down`](#crane_down): A crane descent translates the camera and produces parallax between depth layers.
- [`crop_animation`](#crop_animation): A vertical crop animation keeps perspective constant and shows no motion blur.

**Prompt phrase:** "The camera tilts down slowly from a fixed position."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Tilt Down'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0065, HF-0461

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Tilt Down](https://higgsfield.ai/motion/1958a932-8ffb-4f1a-a5cd-480858f6ae84) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="dolly_in"></a>
### dolly_in

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera physically travels toward the subject, so perspective changes as it approaches.

**Aliases:** Dolly In; dolly-in; push in on dolly; dolly push

**Observable cues**
- Foreground objects grow faster than the background (depth-dependent magnification)
- Occlusion relationships change: background reveals or hides behind foreground edges

**Measurement hints**
- Sustained positive motion.flow_divergence centred on the subject PLUS motion.parallax_ratio clearly above zero between depth layers
- Background scale rate lower than foreground scale rate

**Not to be confused with**
- [`zoom_in`](#zoom_in): A zoom magnifies all depths equally from a fixed viewpoint: no parallax, occlusions stay the same.
- [`apparent_push_in`](#apparent_push_in): Use apparent_push_in when depth separation is too weak to measure parallax.
- [`digital_zoom`](#digital_zoom): A digital zoom also lacks parallax and usually softens detail as it scales.

**Prompt phrase:** "The camera dollies in slowly toward the subject on a smooth track."

**Bindings**
- effectcraft-0.17: approx - layer.newCamera
- higgsfield-camera-controls: exact - preset 'Dolly In'
- higgsfield-camera-controls: approx - preset 'Super Dolly In'
- higgsfield-camera-controls: approx - preset 'Through Object In'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0060, HF-0423

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Dolly In](https://higgsfield.ai/motion/1438937c-a220-4859-93f4-f373da3f73fb) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)

---

<a id="dolly_out"></a>
### dolly_out

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera physically travels away from the subject, so perspective changes as it retreats.

**Aliases:** Dolly Out; pull-back on dolly; dolly back

**Observable cues**
- Foreground shrinks faster than the background; more of the environment is revealed with changing overlap

**Measurement hints**
- Sustained negative motion.flow_divergence plus measurable motion.parallax_ratio between depth layers

**Not to be confused with**
- [`zoom_out`](#zoom_out): A zoom-out widens all depths equally without parallax.
- [`apparent_pull_out`](#apparent_pull_out): Use apparent_pull_out when parallax cannot be measured.

**Prompt phrase:** "The camera dollies out slowly, moving back from the subject."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Dolly Out'
- higgsfield-camera-controls: approx - preset 'Super Dolly Out'
- higgsfield-camera-controls: approx - preset 'Through Object Out'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0060, HF-0425

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Dolly Out](https://higgsfield.ai/motion/a787450c-b2d8-4321-967a-8c302da05949) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)

---

<a id="dolly_left"></a>
### dolly_left

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera translates sideways toward screen-left (a truck move) while keeping its orientation.

**Aliases:** Dolly Left; truck left; lateral tracking

**Observable cues**
- Near objects slide right faster than far objects; background appears to move less

**Measurement hints**
- Rightward global flow whose magnitude decreases with depth (high motion.parallax_ratio); divergence ~0

**Not to be confused with**
- [`pan_left`](#pan_left): A pan rotates in place: all depths slide at nearly the same rate.
- [`tracking_shot`](#tracking_shot): A tracking shot keeps a moving subject roughly fixed in frame while the background streams past.

**Prompt phrase:** "The camera trucks slowly to the left on a level path, parallel to the subject."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Dolly Left'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0424

**Sources**
- [Motion preset: Dolly Left](https://higgsfield.ai/motion/6d7fbb57-6008-4db4-a65c-56a10fc37969) (accessed 2026-11-01)
- [Higgsfield blog: AI Video Camera Control (re-read 2026-11-01)](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Higgsfield Camera Controls public catalog (65 labels, re-read 2026-11-01)](https://higgsfield.ai/camera-controls) (accessed 2026-11-01)

---

<a id="dolly_right"></a>
### dolly_right

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera translates sideways toward screen-right (a truck move) while keeping its orientation.

**Aliases:** Dolly Right; truck right

**Observable cues**
- Near objects slide left faster than far objects

**Measurement hints**
- Leftward global flow whose magnitude decreases with depth (high motion.parallax_ratio); divergence ~0

**Not to be confused with**
- [`pan_right`](#pan_right): A pan rotates in place: all depths slide at nearly the same rate.
- [`tracking_shot`](#tracking_shot): A tracking shot follows a moving subject; a dolly right can pass a static subject.

**Prompt phrase:** "The camera trucks slowly to the right on a level path, parallel to the subject."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Dolly Right'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0426

**Sources**
- [Motion preset: Dolly Right](https://higgsfield.ai/motion/1431d4b2-14d2-4576-876e-c8cec2f5f838) (accessed 2026-11-01)
- [Higgsfield blog: AI Video Camera Control (re-read 2026-11-01)](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Higgsfield Camera Controls public catalog (65 labels, re-read 2026-11-01)](https://higgsfield.ai/camera-controls) (accessed 2026-11-01)

---

<a id="zoom_in"></a>
### zoom_in

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The focal length increases from a fixed viewpoint, magnifying the whole image uniformly.

**Aliases:** Zoom In; optical zoom in

**Observable cues**
- All depth layers enlarge at the same rate; occlusions and perspective stay unchanged
- Background appears to compress as the field of view narrows

**Measurement hints**
- Positive motion.flow_divergence with motion.parallax_ratio ~0; uniform scale term in motion.global_affine
- No upscale softening in frames.sharpness_laplacian_var (otherwise consider digital_zoom)

**Not to be confused with**
- [`dolly_in`](#dolly_in): A dolly-in shows parallax and changing occlusions.
- [`digital_zoom`](#digital_zoom): A digital zoom enlarges pixels in post: sharpness drops and grain scales with the image.
- [`apparent_push_in`](#apparent_push_in): Default to apparent_push_in when parallax and sharpness evidence is inconclusive.

**Prompt phrase:** "The lens zooms in slowly while the camera stays in place."

**Bindings**
- effectcraft-0.17: approx - layer.newCamera
- higgsfield-camera-controls: approx - preset 'Eating Zoom'
- higgsfield-camera-controls: approx - preset 'YoYo Zoom'
- higgsfield-camera-controls: also - preset 'Zoom In'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0061

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Zoom In](https://higgsfield.ai/motion/a3a3db5d-d3c5-4d95-b429-235ae3d1ee82) (accessed 2026-11-01)

---

<a id="zoom_out"></a>
### zoom_out

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The focal length decreases from a fixed viewpoint, widening the whole image uniformly.

**Aliases:** Zoom Out; optical zoom out

**Observable cues**
- All depth layers shrink at the same rate; no occlusion change

**Measurement hints**
- Negative motion.flow_divergence with motion.parallax_ratio ~0; uniform scale term

**Not to be confused with**
- [`dolly_out`](#dolly_out): A dolly-out shows parallax.
- [`apparent_pull_out`](#apparent_pull_out): Use when mechanism is not separable.

**Prompt phrase:** "The lens zooms out slowly while the camera stays in place."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Crash Zoom Out'
- higgsfield-camera-controls: approx - preset 'Rapid Zoom Out'
- higgsfield-camera-controls: also - preset 'YoYo Zoom'
- higgsfield-camera-controls: also - preset 'Zoom Out'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0061

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Zoom Out](https://higgsfield.ai/motion/f9e6792f-b385-4eca-87f6-f439e917a7aa) (accessed 2026-11-01)

---

<a id="crash_zoom_in"></a>
### crash_zoom_in

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

A very fast zoom toward the subject lasting a few frames, often with motion blur.

**Aliases:** Crash Zoom In; Rapid Zoom In; snap zoom

**Observable cues**
- Magnification jumps sharply in under ~0.5 s
- Radial motion blur during the move

**Measurement hints**
- Spike in positive motion.flow_divergence with high peak velocity in motion.velocity_profile; parallax ~0
- motion.motion_blur_streak radial

**Not to be confused with**
- [`punch_in`](#punch_in): A punch-in is an instant scale step at a cut with no intermediate frames.
- [`zoom_in`](#zoom_in): A regular zoom-in is slow and continuous.

**Prompt phrase:** "A sudden crash zoom punches in on the subject."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Crash Zoom In'
- higgsfield-camera-controls: approx - preset 'Mouth In'
- higgsfield-camera-controls: approx - preset 'Rapid Zoom In'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0421, HF-0451

**Sources**
- [Motion preset: Crash Zoom In](https://higgsfield.ai/motion/a2dddb76-03fa-429e-9905-577bffdf9d38) (accessed 2026-11-01)
- [Motion preset: Rapid Zoom In](https://higgsfield.ai/motion/3dee792a-3fb1-40e5-8f46-3a1db42d64b1) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="dolly_zoom"></a>
### dolly_zoom

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera dollies while zooming in the opposite direction, so the subject keeps its size while the background scale changes.

**Aliases:** Dolly Zoom In; Dolly Zoom Out; vertigo effect; contra-zoom

**Observable cues**
- Subject size roughly constant while background expands or contracts
- Strong perspective warp of the background

**Measurement hints**
- motion.subject_track scale ~constant while background divergence is non-zero and opposite in sign to parallax direction

**Not to be confused with**
- [`dolly_in`](#dolly_in): In a plain dolly-in the subject grows.
- [`zoom_in`](#zoom_in): In a plain zoom everything scales together.

**Prompt phrase:** "A dolly zoom: the subject stays the same size while the background stretches away behind it."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Dolly Zoom In'
- higgsfield-camera-controls: exact - preset 'Dolly Zoom Out'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0427, HF-0428

**Sources**
- [Motion preset: Dolly Zoom In](https://higgsfield.ai/motion/114245a3-93fb-434a-9299-44ca9e4656a3) (accessed 2026-11-01)
- [Motion preset: Dolly Zoom Out](https://higgsfield.ai/motion/e057dbd5-1734-4462-bb4c-7d64fe20795e) (accessed 2026-11-01)
- [Higgsfield Camera Controls public catalog (65 labels, re-read 2026-11-01)](https://higgsfield.ai/camera-controls) (accessed 2026-11-01)

---

<a id="crane_up"></a>
### crane_up

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera translates vertically upward (crane or jib), revealing the scene from higher.

**Aliases:** Crane Up; Jib up; boom up; pedestal up

**Observable cues**
- Foreground drops out of frame faster than background
- Viewpoint gains height: more ground plane becomes visible

**Measurement hints**
- Downward global flow with depth-dependent magnitude (motion.parallax_ratio > 0); often combined with tilt_down

**Not to be confused with**
- [`tilt_up`](#tilt_up): A tilt rotates in place without parallax.
- [`apparent_vertical_travel`](#apparent_vertical_travel): Use when parallax is not measurable.

**Prompt phrase:** "The camera cranes up smoothly, rising above the scene."

**Bindings**
- higgsfield-camera-controls: also - preset 'Aerial Pullback'
- higgsfield-camera-controls: approx - preset 'Crane Over The Head'
- higgsfield-camera-controls: exact - preset 'Crane Up'
- higgsfield-camera-controls: approx - preset 'Jib up'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0066, HF-0420, HF-0443

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Crane Up](https://higgsfield.ai/motion/45d7f47f-2c7b-4c5e-84b7-943758a39dcc) (accessed 2026-11-01)
- [Motion preset: Jib up](https://higgsfield.ai/motion/d6b43086-d5d1-415b-a239-016698b425d7) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="crane_down"></a>
### crane_down

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera translates vertically downward (crane or jib) toward the subject level.

**Aliases:** Crane Down; Jib down; boom down

**Observable cues**
- Foreground rises into frame faster than background; viewpoint loses height

**Measurement hints**
- Upward global flow with depth-dependent magnitude (motion.parallax_ratio > 0)

**Not to be confused with**
- [`tilt_down`](#tilt_down): A tilt rotates in place without parallax.
- [`apparent_vertical_travel`](#apparent_vertical_travel): Use when parallax is not measurable.

**Prompt phrase:** "The camera cranes down smoothly toward the subject."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Crane Down'
- higgsfield-camera-controls: approx - preset 'Jib down'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0066, HF-0418, HF-0442

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Crane Down](https://higgsfield.ai/motion/494db3c2-2297-4cf7-bef7-cba0cebe73ee) (accessed 2026-11-01)
- [Motion preset: Jib down](https://higgsfield.ai/motion/4e2318ed-572e-4d5a-bcf9-7e70e4755a52) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="arc_left"></a>
### arc_left

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera travels along a curved path around the subject toward screen-left, keeping it near frame centre.

**Aliases:** Arc Left; arc shot left

**Observable cues**
- Subject stays roughly centred while its visible side changes
- Background sweeps in the opposite direction behind the subject

**Measurement hints**
- Subject region low flow while background flow is high and opposite (motion.subject_vs_background); curl around subject centroid

**Not to be confused with**
- [`subject_rotation`](#subject_rotation): If the background is static and only the subject turns, the subject rotates (3D Rotation), not the camera.
- [`pan_right`](#pan_right): A pan moves the subject across frame instead of keeping it centred.

**Prompt phrase:** "The camera arcs slowly to the left around the subject."

**Bindings**
- higgsfield-camera-controls: also - preset 'Bullet Time'
- higgsfield-camera-controls: exact - preset 'Arc Left'
- higgsfield-camera-controls: approx - preset 'Glam'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0067, HF-0413

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Arc Left](https://higgsfield.ai/motion/2a5d8f86-aef3-4b34-b5ee-fb2020daa131) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="arc_right"></a>
### arc_right

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera travels along a curved path around the subject toward screen-right, keeping it near frame centre.

**Aliases:** Arc Right

**Observable cues**
- Subject stays centred while its visible side changes; background sweeps opposite

**Measurement hints**
- Subject region low flow, background high opposite flow; curl around subject centroid

**Not to be confused with**
- [`subject_rotation`](#subject_rotation): A rotating product over a static background is subject motion.
- [`pan_left`](#pan_left): A pan moves the subject across the frame.

**Prompt phrase:** "The camera arcs slowly to the right around the subject."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Arc Right'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0067, HF-0472

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Arc Right](https://higgsfield.ai/motion/0bdbf318-f918-4f9b-829a-74cab681d806) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="orbit_360"></a>
### orbit_360

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera completes (or nearly completes) a full circuit around a stationary subject.

**Aliases:** 360 Orbit; orbit; orbital move; Lazy Susan (camera); Hero Cam (fast orbit)

**Observable cues**
- Every side of the subject is shown while the environment rotates behind it
- Background completes a full sweep

**Measurement hints**
- Continuous background flow in one direction across the whole shot with subject centred; cumulative background rotation ~360 degrees

**Not to be confused with**
- [`subject_rotation`](#subject_rotation): In a turntable shot the background does not move; the subject spins.
- [`arc_left`](#arc_left): An arc covers only part of the circle.

**Prompt phrase:** "The camera orbits a full 360 degrees around the stationary subject."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Hero Cam'
- higgsfield-camera-controls: approx - preset 'Lazy Susan'
- higgsfield-camera-controls: exact - preset '360 Orbit'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0067, HF-0469, HF-0444

**Sources**
- [Motion preset: 360 Orbit](https://higgsfield.ai/motion/d7c180bc-793c-4d29-83ba-c2d5e84e53d4) (accessed 2026-11-01)
- [Motion preset: Lazy Susan](https://higgsfield.ai/motion/025866ff-677c-4af2-92ef-52d6ec3b035e) (accessed 2026-11-01)
- [Motion preset: Hero Cam](https://higgsfield.ai/motion/a8c54413-c991-416a-8ac8-32c6a42caa6c) (accessed 2026-11-01)
- [Higgsfield blog: AI Video Camera Control (re-read 2026-11-01)](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="tracking_shot"></a>
### tracking_shot

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The camera moves alongside or behind a moving subject, keeping it at a roughly constant place in frame.

**Aliases:** tracking; track; follow shot; walking follow; Head Tracking; Double Dolly

**Observable cues**
- Subject keeps its frame position and size while the background streams past
- Motion blur on the background, not on the subject

**Measurement hints**
- Low subject flow vs high background flow (motion.subject_vs_background) sustained over the shot; parallax present

**Not to be confused with**
- [`pan_left`](#pan_left): A pan can follow a subject, but from a fixed point: no parallax.
- [`dolly_left`](#dolly_left): A dolly can pass a static subject; tracking follows a moving one.

**Prompt phrase:** "A smooth tracking shot follows the subject at a constant distance."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Car Chasing'
- higgsfield-camera-controls: approx - preset 'Double Dolly'
- higgsfield-camera-controls: approx - preset 'Head Tracking'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0062, HF-0438, HF-0429

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)
- [Sports Product Video Ads](https://higgsfield.ai/blog/sports-product-video-ads-ai-2026) (accessed 2026-11-01)
- [Motion preset: Head Tracking](https://higgsfield.ai/motion/fe520e06-7971-4f28-9e10-e45911c57bb6) (accessed 2026-11-01)

---

<a id="whip_pan"></a>
### whip_pan

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

An extremely fast pan that smears the image into directional motion blur, often used to bridge shots.

**Aliases:** Whip Pan; whip-pan; swish pan

**Observable cues**
- Frames dominated by horizontal streaks; content unreadable for a few frames

**Measurement hints**
- Spike in horizontal flow magnitude and motion.motion_blur_streak over 2-8 frames; frames.sharpness_laplacian_var collapses then recovers

**Not to be confused with**
- [`whip_transition`](#whip_transition): If the blur hides a cut between two different shots, record whip_transition in montage.transition as well.
- [`pan_left`](#pan_left): A regular pan keeps the image readable.

**Prompt phrase:** "A fast whip pan smears the frame with motion blur."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Whip Pan'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0068, HF-0466

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Whip Pan](https://higgsfield.ai/motion/7a144766-cdd2-4b73-8a27-67b35f2d4ba2) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="apparent_push_in"></a>
### apparent_push_in

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The subject grows in frame as if the camera approached, but the evidence cannot separate dolly, zoom, digital zoom or crop.

**Aliases:** push-in; push in; Eyes In; Zoom In (apparent)

**Observable cues**
- Subject and background enlarge over time
- Depth separation too weak, or the scene too flat, to measure parallax

**Measurement hints**
- Positive motion.flow_divergence with inconclusive motion.parallax_ratio; claim must list dolly_in, zoom_in, digital_zoom, crop_animation as alternatives

**Not to be confused with**
- [`dolly_in`](#dolly_in): Promote to dolly_in only with measurable parallax.
- [`zoom_in`](#zoom_in): Promote to zoom_in only with clear zero parallax across separated depth layers and no upscale softening.

**Prompt phrase:** "A slow push-in toward the subject."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Eyes In'
- higgsfield-camera-controls: exact - preset 'Zoom In'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris analysis term derived from the documented distinction 'Push-in / pull-back: specify the intended camera mechanism'.

**Dictionary:** HF-0063, HF-0410, HF-0470

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Eyes In](https://higgsfield.ai/motion/3afdf962-2709-44a9-a41c-6565e6998529) (accessed 2026-11-01)
- [Motion preset: Zoom In](https://higgsfield.ai/motion/a3a3db5d-d3c5-4d95-b429-235ae3d1ee82) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="apparent_pull_out"></a>
### apparent_pull_out

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The subject shrinks in frame as if the camera retreated, but the mechanism cannot be separated.

**Aliases:** pull-back; pullback; Zoom Out (apparent); reveal pull-out

**Observable cues**
- More of the surroundings becomes visible over time

**Measurement hints**
- Negative motion.flow_divergence with inconclusive parallax; list dolly_out, zoom_out, digital_zoom as alternatives

**Not to be confused with**
- [`dolly_out`](#dolly_out): Requires measurable parallax.
- [`zoom_out`](#zoom_out): Requires clear zero parallax with separated depth layers.

**Prompt phrase:** "A slow pull-back that reveals the surroundings."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Aerial Pullback'
- higgsfield-camera-controls: approx - preset 'BTS'
- higgsfield-camera-controls: also - preset 'Rapid Zoom Out'
- higgsfield-camera-controls: exact - preset 'Zoom Out'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0063, HF-0471

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Zoom Out](https://higgsfield.ai/motion/f9e6792f-b385-4eca-87f6-f439e917a7aa) (accessed 2026-11-01)
- [Motion preset: BTS](https://higgsfield.ai/motion/b779cfda-9624-4f61-80bc-f5d0461f3959) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="apparent_lateral_travel"></a>
### apparent_lateral_travel

dimension `camera.movement` | unit `shot` | claim `estimated` | verified

The scene slides sideways as if the camera moved laterally, but pan, truck and crop cannot be separated.

**Aliases:** lateral travel; lateral move; slide

**Observable cues**
- Horizontal global motion over a scene with little depth separation

**Measurement hints**
- Dominant horizontal flow with inconclusive motion.parallax_ratio; list pan_*, dolly_left/right, crop_animation as alternatives

**Not to be confused with**
- [`pan_left`](#pan_left): Promote to a pan when distant and near layers provably move at the same rate.
- [`dolly_left`](#dolly_left): Promote to a dolly when parallax is measurable.

**Prompt phrase:** "The view drifts slowly sideways."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris analysis term; the guide's 'Pan versus lateral travel' distinction supports it.

**Dictionary:** HF-0085

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [VFX in 4K](https://higgsfield.ai/blog/vfx_4k) (accessed 2026-11-01)

---

<a id="apparent_vertical_travel"></a>
### apparent_vertical_travel

dimension `camera.movement` | unit `shot` | claim `estimated` | **unverified**

The scene slides vertically as if the camera rose or descended, but tilt, crane and crop cannot be separated.

**Aliases:** vertical travel

**Observable cues**
- Vertical global motion over a scene with little depth separation (e.g. top-down table shots)

**Measurement hints**
- Dominant vertical flow with inconclusive motion.parallax_ratio; list tilt_*, crane_*, crop_animation as alternatives

**Not to be confused with**
- [`tilt_up`](#tilt_up): Promote to a tilt when the horizon or verticals show rotation without parallax.
- [`crane_up`](#crane_up): Promote to a crane when parallax is measurable.

**Prompt phrase:** "The view drifts slowly upward."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris analysis term by symmetry with apparent_lateral_travel; no Higgsfield source names it.

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)

---

<a id="dim-camera-shot_size"></a>
## camera.shot_size

Temporal unit `shot`, cardinality `single`.

Framing scale of the principal subject, measured from the subject or face bounding box relative to frame height. For a vertical 1080x1920 frame the thresholds below are starting values to calibrate in the pilot.

Measurement keys: `motion.subject_scale_ratio`, `motion.subject_track`, `sheets.keyframes`

<a id="wide_shot"></a>
### wide_shot

dimension `camera.shot_size` | unit `shot` | claim `measured` | verified

The subject is shown within substantial surroundings; the environment carries as much information as the subject.

**Aliases:** WS; wide; long shot; establishing shot; extreme wide shot

**Observable cues**
- Whole subject visible with large margins
- Setting readable

**Measurement hints**
- Person bbox height < ~0.5 of frame height, or object occupies < ~15% of frame area

**Not to be confused with**
- [`full_shot`](#full_shot): A full shot fits the whole body tightly; a wide shot leaves the environment dominant.

**Prompt phrase:** "Wide shot showing the subject within the full setting."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0026, HF-0027

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="full_shot"></a>
### full_shot

dimension `camera.shot_size` | unit `shot` | claim `measured` | verified

The entire subject (head to toe for a person, whole object or table for food) fills most of the frame height.

**Aliases:** full-body; full-length; FS

**Observable cues**
- Head and feet both inside the frame with little margin

**Measurement hints**
- Person bbox height ~0.75-1.0 of frame height with both extremities inside

**Not to be confused with**
- [`medium_shot`](#medium_shot): A medium shot cuts the body around the waist.

**Prompt phrase:** "Full shot, the whole subject visible head to toe."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0034

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)

---

<a id="medium_shot"></a>
### medium_shot

dimension `camera.shot_size` | unit `shot` | claim `measured` | verified

The subject is framed from around the waist up, or an object fills about half of the frame.

**Aliases:** MS; mid shot; waist shot

**Observable cues**
- Frame edge cuts the body near the waist; hands and gestures readable

**Measurement hints**
- Face bbox height ~0.08-0.15 of frame height; person cut between hip and chest

**Not to be confused with**
- [`medium_close_up`](#medium_close_up): A medium close-up cuts at the chest and the face dominates.

**Prompt phrase:** "Medium shot from the waist up."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0028

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)

---

<a id="medium_close_up"></a>
### medium_close_up

dimension `camera.shot_size` | unit `shot` | claim `measured` | verified

Framing between medium shot and close-up, cutting around the chest or shoulders.

**Aliases:** MCU; head-and-shoulders

**Observable cues**
- Face and shoulders dominate; background still partly readable

**Measurement hints**
- Face bbox height ~0.15-0.25 of frame height

**Not to be confused with**
- [`close_up`](#close_up): A close-up makes the face fill most of the frame.

**Prompt phrase:** "Medium close-up, chest and face."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0029, HF-0035

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)

---

<a id="close_up"></a>
### close_up

dimension `camera.shot_size` | unit `shot` | claim `measured` | verified

A tight framing on a face, a hand action or a single dish where the subject fills most of the frame.

**Aliases:** CU; tight close-up; insert close-up

**Observable cues**
- Face or object fills most of the frame; background reduced to colour or blur

**Measurement hints**
- Face bbox height ~0.25-0.5 of frame height, or object > ~50% of frame area

**Not to be confused with**
- [`extreme_close_up`](#extreme_close_up): An extreme close-up isolates a part (eyes, a crumb, a droplet).

**Prompt phrase:** "Close-up on the subject."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0030, HF-0033

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="extreme_close_up"></a>
### extreme_close_up

dimension `camera.shot_size` | unit `shot` | claim `measured` | verified

A very tight framing of a small part of the subject: eyes, lips, a fork tine, a droplet.

**Aliases:** ECU; XCU

**Observable cues**
- Only a fragment of the subject is visible; texture dominates

**Measurement hints**
- Face bbox height > ~0.5 of frame (face cropped), or object part fills the frame

**Not to be confused with**
- [`macro_shot`](#macro_shot): Macro implies magnification of very small detail, often with razor-thin focus; extreme close-up is about framing a part.

**Prompt phrase:** "Extreme close-up on a small detail."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0031

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="macro_shot"></a>
### macro_shot

dimension `camera.shot_size` | unit `shot` | claim `estimated` | verified

A close view that reveals small-scale detail beyond normal viewing distance, typically with very shallow focus.

**Aliases:** macro; Macro shot

**Observable cues**
- Surface micro-texture (pores, crystals, droplets) visible
- Focus falloff within millimetres

**Measurement hints**
- Extreme close framing plus high local sharpness at a thin band in frames.sharpness_map_grid

**Not to be confused with**
- [`extreme_close_up`](#extreme_close_up): Extreme close-up crops a part of a person or object without necessarily magnifying micro-texture.

**Prompt phrase:** "Macro shot revealing fine surface texture and droplets."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** A macro look is not proof of a macro lens.

**Dictionary:** HF-0032

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="dim-camera-angle"></a>
## camera.angle

Temporal unit `shot`, cardinality `multi`.

Vertical viewpoint and roll of the camera relative to the subject, plus viewpoint conventions (POV, over-the-shoulder). One vertical angle (eye_level, low_angle, high_angle, top_down) applies at a time; dutch_angle, pov and over_the_shoulder may co-occur.

- Mutually exclusive: eye_level, low_angle, high_angle, top_down

Measurement keys: `frames.horizon_angle_deg`, `motion.subject_track`, `sheets.keyframes`

<a id="eye_level"></a>
### eye_level

dimension `camera.angle` | unit `shot` | claim `estimated` | verified

The camera sits near the subject's eye height (or table height for food), looking straight on.

**Aliases:** eye-level; straight-on

**Observable cues**
- Horizon passes near the subject's eyes
- Vertical lines stay parallel

**Measurement hints**
- Vanishing point near subject eye line; little vertical convergence

**Not to be confused with**
- [`high_angle`](#high_angle): A high angle shows the top surfaces of objects (tabletop visible).

**Prompt phrase:** "Eye-level camera, straight on."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0044

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)

---

<a id="low_angle"></a>
### low_angle

dimension `camera.angle` | unit `shot` | claim `estimated` | verified

The camera looks upward at the subject from below its eye or table line.

**Aliases:** low angle; worm's-eye; ground-level; Buckle Up (from below)

**Observable cues**
- Underside of objects or chin visible
- Verticals converge upward; ceiling or sky behind the subject

**Measurement hints**
- Vanishing point above frame; subject top larger relative to base

**Not to be confused with**
- [`dutch_angle`](#dutch_angle): Dutch tilts the horizon (roll), not the pitch.

**Prompt phrase:** "Low angle looking up at the subject."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Buckle Up'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0042, HF-0047, HF-0415

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Motion preset: Buckle Up](https://higgsfield.ai/motion/4ef72175-227a-418b-923d-2831dcdf7d4f) (accessed 2026-11-01)
- [Cinematic Car Commercial](https://higgsfield.ai/blog/ai-car-commercial-youtube-guide) (accessed 2026-11-01)
- [Higgsfield Angles](https://higgsfield.ai/blog/Change-the-Angle-of-Any-Image) (accessed 2026-11-01)

---

<a id="high_angle"></a>
### high_angle

dimension `camera.angle` | unit `shot` | claim `estimated` | verified

The camera looks down at the subject from above its eye or table line, but not vertically.

**Aliases:** high angle; bird's-eye view

**Observable cues**
- Top surfaces visible (plate rims as ellipses)
- Verticals converge downward

**Measurement hints**
- Ellipse ratio of circular objects between ~0.3 and ~0.9 (food plates)

**Not to be confused with**
- [`top_down`](#top_down): Top-down is vertical: circles appear as circles.

**Prompt phrase:** "High angle looking down at the subject."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0043, HF-0045

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)
- [Higgsfield Angles](https://higgsfield.ai/blog/Change-the-Angle-of-Any-Image) (accessed 2026-11-01)

---

<a id="top_down"></a>
### top_down

dimension `camera.angle` | unit `shot` | claim `estimated` | verified

The camera points straight down at the scene (flat lay), so circular plates appear as circles.

**Aliases:** overhead; flat lay; Overhead; 90-degree overhead

**Observable cues**
- Plates and bowls look perfectly round
- No horizon; table surface fills the frame

**Measurement hints**
- Ellipse ratio of circular objects > ~0.9; no vanishing point

**Not to be confused with**
- [`high_angle`](#high_angle): A high angle still shows perspective convergence and elliptical plates.

**Prompt phrase:** "Top-down overhead flat lay, camera pointing straight down."

**Bindings**
- higgsfield-camera-controls: also - preset 'Crane Over The Head'
- higgsfield-camera-controls: approx - preset 'Overhead'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0046, HF-0448

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Motion preset: Overhead](https://higgsfield.ai/motion/b6395b91-a356-4bc6-9cda-fc2793b3d706) (accessed 2026-11-01)
- [Higgsfield Angles](https://higgsfield.ai/blog/Change-the-Angle-of-Any-Image) (accessed 2026-11-01)

---

<a id="dutch_angle"></a>
### dutch_angle

dimension `camera.angle` | unit `shot` | claim `measured` | verified

The camera is rolled so the horizon and verticals are deliberately tilted.

**Aliases:** Dutch Angle; canted angle; dutch tilt

**Observable cues**
- Horizon or verticals tilted by more than a few degrees

**Measurement hints**
- |frames.horizon_angle_deg| > ~5 degrees sustained across the shot (not a transient shake)

**Not to be confused with**
- [`added_shake`](#added_shake): Shake creates transient roll; dutch is a sustained tilt.
- [`low_angle`](#low_angle): A low angle changes pitch; verticals converge but the horizon stays level.

**Prompt phrase:** "Dutch angle with the horizon tilted."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Dutch Angle'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0086, HF-0430

**Sources**
- [Motion preset: Dutch Angle](https://higgsfield.ai/motion/28a18555-b8ed-4cac-aad6-40ecaaad9345) (accessed 2026-11-01)
- [Higgsfield Camera Controls public catalog (65 labels, re-read 2026-11-01)](https://higgsfield.ai/camera-controls) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="pov"></a>
### pov

dimension `camera.angle` | unit `shot` | claim `interpreted` | verified

The viewpoint represents what a participant sees (first-person), often with hands entering from the bottom of frame.

**Aliases:** POV; first-person; Object POV

**Observable cues**
- Hands or held objects enter from the lower frame edge
- Camera height and motion follow a human head

**Measurement hints**
- Hands detected entering from bottom edge; head-like motion signature in motion.flow_jitter

**Not to be confused with**
- [`selfie`](#selfie): A selfie faces the operator; POV faces away from them.
- [`over_the_shoulder`](#over_the_shoulder): OTS includes the observer's shoulder or head in frame.

**Prompt phrase:** "First-person POV shot, hands entering from the bottom of frame."

**Bindings**
- higgsfield-camera-controls: approx - preset 'Object POV'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0075, HF-0447

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Motion preset: Object POV](https://higgsfield.ai/motion/ab14b29d-f23e-449e-a40e-ebdbb4f7437a) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="over_the_shoulder"></a>
### over_the_shoulder

dimension `camera.angle` | unit `shot` | claim `interpreted` | verified

The view looks past one person's shoulder or head toward another subject or screen.

**Aliases:** OTS; over-shoulder

**Observable cues**
- Blurred shoulder or head occupies a frame edge in the foreground

**Measurement hints**
- Large defocused foreground mass at one frame edge plus a sharper subject beyond

**Not to be confused with**
- [`pov`](#pov): POV shows no part of the observer's own shoulder or head.

**Prompt phrase:** "Over-the-shoulder shot looking toward the subject."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0037

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="dim-camera-support"></a>
## camera.support

Temporal unit `shot`, cardinality `single`.

The rig or carrying method that the camera motion signature implies (or that a synthetic shot emulates). Inferred from motion texture (jitter spectrum, path smoothness), so the default claim is estimated.

Measurement keys: `motion.flow_jitter`, `motion.global_affine`, `motion.velocity_profile`, `motion.subject_track`

<a id="locked_off"></a>
### locked_off

dimension `camera.support` | unit `shot` | claim `measured` | verified

The camera is fixed on a tripod or clamp: zero path motion and zero jitter.

**Aliases:** locked off; tripod; sticks; locked-off tripod

**Observable cues**
- Rock-steady frame edges against background features

**Measurement hints**
- motion.flow_jitter at noise floor and motion.global_affine ~0 over the whole shot

**Not to be confused with**
- [`steadicam`](#steadicam): A stabilised rig still moves through space; locked-off does not move.
- [`handheld`](#handheld): Handheld held still still shows small low-frequency drift.

**Related:** produces [`static`](#static)

**Prompt phrase:** "Locked-off tripod shot."

**Bindings**
- higgsfield-camera-controls: also - preset 'Static'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0070, HF-0072

**Sources**
- [Kling 4.0 and 3.0 Prompt Guide](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="handheld"></a>
### handheld

dimension `camera.support` | unit `shot` | claim `estimated` | verified

The camera is carried by hand or on the shoulder, producing irregular low-amplitude motion and micro-corrections.

**Aliases:** Handheld; shoulder-mounted; handheld drift; breathing sway; Wiggle

**Observable cues**
- Small irregular drift and bob; breathing sway
- Framing corrections after subject movement

**Measurement hints**
- Elevated motion.flow_jitter with energy around ~0.5-4 Hz; non-smooth motion.velocity_profile

**Not to be confused with**
- [`added_shake`](#added_shake): Shake added in post is periodic or noise-like, identical across depth layers, and often shows crop margins scaling.
- [`steadicam`](#steadicam): Steadicam paths are smooth with floating, low-jitter motion.

**Prompt phrase:** "Handheld camera with subtle natural sway and micro-corrections."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Handheld'
- higgsfield-camera-controls: approx - preset 'Wiggle'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0069, HF-0073, HF-0079, HF-0080, HF-0437

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Motion preset: Handheld](https://higgsfield.ai/motion/cf529456-6478-4622-a572-052f0d8ae378) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)

---

<a id="steadicam"></a>
### steadicam

dimension `camera.support` | unit `shot` | claim `estimated` | verified

A body-supported or gimbal-stabilised moving camera: travels through space with smooth, floating motion.

**Aliases:** Steadicam; gimbal; gyro-rig; stabilised

**Observable cues**
- Camera moves through the scene but frame stays smooth, without bumps

**Measurement hints**
- Sustained translation with low motion.flow_jitter and smooth velocity changes

**Not to be confused with**
- [`handheld`](#handheld): Handheld has visible jitter.
- [`robot_arm`](#robot_arm): Robot-arm moves are faster, perfectly repeatable and machine-precise, often with abrupt start and stop.

**Prompt phrase:** "Smooth Steadicam move gliding through the space."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0071

**Sources**
- [AI Video Camera Control](https://higgsfield.ai/blog/ai-video-camera-control) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="robot_arm"></a>
### robot_arm

dimension `camera.support` | unit `shot` | claim `estimated` | verified

A motion-control robotic arm: fast, precise, repeatable paths with crisp acceleration, typical of food and product commercials.

**Aliases:** Robot arm; Robo Arm; motion control

**Observable cues**
- Very fast moves that stop dead on a perfectly framed product
- Geometric, machine-precise path

**Measurement hints**
- High peak velocity with near-zero jitter and very short deceleration in motion.velocity_profile

**Not to be confused with**
- [`steadicam`](#steadicam): Steadicam moves are slower, floating and organic.
- [`crash_zoom_in`](#crash_zoom_in): A crash zoom changes focal length; robot arm moves the camera with parallax.

**Prompt phrase:** "High-speed robotic camera arm move that stops precisely on the product."

**Bindings**
- higgsfield-camera-controls: exact - preset 'Robo Arm'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0077, HF-0454

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Motion preset: Robo Arm](https://higgsfield.ai/motion/1bd4363a-6e5a-4c57-90a5-30f0733a769b) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="drone"></a>
### drone

dimension `camera.support` | unit `shot` | claim `estimated` | verified

An aerial camera (drone or helicopter) flying above or through the scene.

**Aliases:** aerial; Helicopter shot; FPV Drone; Aerial Pullback

**Observable cues**
- Elevated viewpoint moving through open space
- Ground plane recedes with large parallax

**Measurement hints**
- Large translation with strong parallax from an elevated viewpoint; top-of-frame horizon

**Not to be confused with**
- [`crane_up`](#crane_up): A crane rise is limited in height and stays tethered to a point.

**Prompt phrase:** "Aerial drone shot gliding above the scene."

**Bindings**
- higgsfield-camera-controls: also - preset 'Aerial Pullback'
- higgsfield-camera-controls: approx - preset 'FPV Drone'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0076, HF-0435

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Motion preset: FPV Drone](https://higgsfield.ai/motion/5eb82f94-2b98-4e4a-ab4b-ee6c872fb2c7) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="selfie"></a>
### selfie

dimension `camera.support` | unit `shot` | claim `estimated` | verified

The operator holds the phone at arm's length facing themselves (front camera), the dominant creator-video setup.

**Aliases:** handheld selfie; front camera; arm's-length selfie

**Observable cues**
- Face centred and close, arm or shoulder visible at a frame edge
- Slight wide-angle distortion of the face

**Measurement hints**
- Face bbox stable near centre with handheld jitter; one arm exiting the frame edge

**Not to be confused with**
- [`pov`](#pov): POV faces away from the operator.
- [`handheld`](#handheld): Generic handheld is not necessarily self-facing.

**Prompt phrase:** "Handheld selfie at arm's length, front-facing phone camera."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** The phrase 'handheld selfie' appears in the Seedance 2.5 guide.

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="virtual_camera"></a>
### virtual_camera

dimension `camera.support` | unit `shot` | claim `estimated` | **unverified**

No physical camera: the frame is a screen recording, motion graphic or fully synthetic render with a perfect, non-physical viewpoint.

**Aliases:** screen capture; virtual camera; CG camera

**Observable cues**
- Pixel-perfect UI, flat graphics, no sensor noise, no lens artefacts

**Measurement hints**
- frames.noise_residual near zero, flat colour regions, exact repeated pixels; motion is purely 2D affine

**Not to be confused with**
- [`locked_off`](#locked_off): A locked-off camera still records noise, lens softness and real light.

**Prompt phrase:** "Clean digital render with a perfectly stable virtual camera."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris extension for screen recordings and motion graphics; no Higgsfield term.

**Dictionary:** HF-0232

**Sources**
- [AI Animation Generator](https://higgsfield.ai/ai-animation-generator) (accessed 2026-11-01)

---

<a id="dim-subject-action"></a>
## subject.action

Temporal unit `shot`, cardinality `multi`.

Independent movement of the subject or product (layer 2 of the four motion layers), kept separate from camera movement.

Measurement keys: `motion.subject_track`, `motion.subject_vs_background`, `motion.flow_curl`, `sheets.keyframes`

<a id="subject_rotation"></a>
### subject_rotation

dimension `subject.action` | unit `shot` | claim `estimated` | verified

The subject or product turns in place (turntable) while the camera and background stay still.

**Aliases:** 3D Rotation; turntable; product spin

**Observable cues**
- Background static; product silhouette and visible face change over time

**Measurement hints**
- High motion.flow_curl inside the subject mask with background flow ~0

**Not to be confused with**
- [`orbit_360`](#orbit_360): In an orbit the background moves behind the subject.
- [`arc_left`](#arc_left): An arc moves the camera; background shifts.

**Prompt phrase:** "The product rotates slowly in place on a turntable while the camera stays still."

**Bindings**
- higgsfield-camera-controls: exact - preset '3D Rotation'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0473

**Sources**
- [Motion preset: 3D Rotation](https://higgsfield.ai/motion/6f06f47e-922e-4660-9fe9-754e4be69696) (accessed 2026-11-01)

---

<a id="pour_shot"></a>
### pour_shot

dimension `subject.action` | unit `shot` | claim `estimated` | verified

A liquid or loose ingredient is poured, drizzled or splashed into or over the subject.

**Aliases:** Splash / pour shot; splash; drizzle; pour

**Observable cues**
- Continuous stream or droplets moving downward; splash crowns on impact

**Measurement hints**
- Localised high downward flow in a narrow region; short high-frequency events at impact

**Not to be confused with**
- Dropped solid ingredients bounce and settle; pours are continuous streams.

**Prompt phrase:** "Thick sauce pours slowly over the dish, catching the light."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0269, HF-0270

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="hand_interaction"></a>
### hand_interaction

dimension `subject.action` | unit `shot` | claim `estimated` | verified

Hands enter and act on the subject: picking, cutting, placing, tapping a phone screen.

**Aliases:** hand action; contact points

**Observable cues**
- Hands visible with contact points on the object

**Measurement hints**
- Hand detections intersecting subject mask; subject displacement after contact

**Not to be confused with**
- [`pov`](#pov): Hands in POV come from the bottom edge; hand_interaction can be from any side and is about the action itself.

**Prompt phrase:** "A hand enters from screen-right and lifts a portion with a fork."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0217

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="dim-optics"></a>
## optics

Temporal unit `shot`, cardinality `multi`.

Lens and capture appearance: focus, depth of field, field of view, flare, halation, vignetting, motion blur, diffusion. These describe what the pixels look like, never the physical lens used: focal length, aperture and mm values are only allowed as claim_kind designed in direction.json.

Measurement keys: `frames.sharpness_laplacian_var`, `frames.sharpness_map_grid`, `frames.edge_falloff_luma`, `frames.highlight_bloom`, `frames.line_curvature`, `motion.motion_blur_streak`, `motion.parallax_ratio`, `frames.clip_highlights`

<a id="shallow_depth_of_field"></a>
### shallow_depth_of_field

dimension `optics` | unit `shot` | claim `estimated` | verified

Only a thin depth slice is sharp; foreground and background fall into strong blur.

**Aliases:** shallow DOF; f/1.4 Wide Open; thin focus; shallow focus; bokeh; oval bokeh

**Observable cues**
- Subject edges crisp while background is soft or bokeh
- Blur increases with distance from the focus plane

**Measurement hints**
- High variance of frames.sharpness_map_grid: subject cells sharp, background cells < ~30% of subject sharpness
- Blur gradient correlates with estimated depth

**Not to be confused with**
- [`diffusion`](#diffusion): Diffusion softens the whole frame (glow on highlights) regardless of depth.
- [`motion_blur`](#motion_blur): Motion blur is directional and follows movement, not depth.

**Related:** realizes [`dof`](#dof)

**Prompt phrase:** "Shallow depth of field, the subject tack sharp against a creamy blurred background."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.blur.cameralens
- higgsfield-cinema-4.0: exact - camera_aperture_id=<f/1.4 Wide Open>
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0100, HF-0098, HF-0105

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)
- [Cinematic Headphones · Ultra-Realistic Ads](https://higgsfield.ai/blog/cinematic_headphones) (accessed 2026-11-01)

---

<a id="deep_focus"></a>
### deep_focus

dimension `optics` | unit `shot` | claim `estimated` | verified

Near and far planes both appear acceptably sharp.

**Aliases:** deep focus; f/11 Deep Focus; deep depth of field

**Observable cues**
- Background texture and text legible together with the foreground subject

**Measurement hints**
- Low spread of frames.sharpness_map_grid across depth layers

**Not to be confused with**
- [`shallow_depth_of_field`](#shallow_depth_of_field): In shallow DOF the background is visibly blurred.

**Prompt phrase:** "Deep focus, foreground and background both sharp."

**Bindings**
- higgsfield-cinema-4.0: exact - camera_aperture_id=<f/11 Deep Focus>
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0101

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)

---

<a id="rack_focus"></a>
### rack_focus

dimension `optics` | unit `shot` | claim `estimated` | verified

The focus plane shifts during the shot from one subject or depth to another.

**Aliases:** Rack focus; focus pull; Focus Change; pull focus

**Observable cues**
- One region sharpens while another softens within the same shot
- Possible slight framing breathing

**Measurement hints**
- Opposite-sign trends of sharpness in two regions of frames.sharpness_map_grid within one shot, with stable framing

**Not to be confused with**
- [`autofocus_hunting`](#autofocus_hunting): Hunting oscillates back and forth without settling; a rack is a deliberate single transition.
- [`cross_dissolve`](#cross_dissolve): A dissolve blends two images; a rack keeps one continuous image.

**Prompt phrase:** "Rack focus from the foreground subject to the background."

**Bindings**
- effectcraft-0.17: approx - layer.newCamera
- higgsfield-camera-controls: exact - preset 'Focus Change'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0103, HF-0434

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Motion preset: Focus Change](https://higgsfield.ai/motion/390e084a-4a80-410b-a808-77411828c61d) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="wide_angle_lens"></a>
### wide_angle_lens

dimension `optics` | unit `shot` | claim `estimated` | verified

A broad field-of-view look: exaggerated perspective, stretched edges, strong size difference between near and far.

**Aliases:** wide-angle; classic wide; 24mm look

**Observable cues**
- Close objects look large and far objects tiny
- Straight lines lean near frame edges

**Measurement hints**
- Strong convergence of verticals near edges; large near/far scale ratio for similar objects

**Not to be confused with**
- [`fisheye`](#fisheye): Fisheye bends straight lines into curves; rectilinear wide keeps lines straight.
- [`telephoto_lens`](#telephoto_lens): Telephoto compresses depth.

**Prompt phrase:** "Wide-angle lens look with exaggerated perspective."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0089

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="telephoto_lens"></a>
### telephoto_lens

dimension `optics` | unit `shot` | claim `estimated` | verified

A narrow field-of-view look that compresses depth: background appears large and close behind the subject.

**Aliases:** telephoto; short telephoto; compressed background

**Observable cues**
- Background elements look stacked close to the subject
- Little perspective convergence

**Measurement hints**
- Small near/far scale ratio; low line convergence; usually with shallow depth of field

**Not to be confused with**
- [`wide_angle_lens`](#wide_angle_lens): Wide angle exaggerates depth.

**Prompt phrase:** "Telephoto look with a compressed background."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0090

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)

---

<a id="fisheye"></a>
### fisheye

dimension `optics` | unit `shot` | claim `measured` | verified

An ultra-wide look in which straight lines bow into curves around the frame centre.

**Aliases:** Fisheye; fisheye curve; barrel distortion

**Observable cues**
- Straight architectural or table edges curve outward
- Bulging centre

**Measurement hints**
- High frames.line_curvature that increases toward the frame edges

**Not to be confused with**
- [`wide_angle_lens`](#wide_angle_lens): Rectilinear wide-angle keeps straight lines straight.

**Prompt phrase:** "Fisheye lens look with curved edges."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.distort.opticscompensation
- ffmpeg: approx - lenscorrection
- higgsfield-camera-controls: exact - preset 'Fisheye'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0432

**Sources**
- [Motion preset: Fisheye](https://higgsfield.ai/motion/6c689fc3-e421-4ed5-892c-2092d1c60be0) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="lens_flare"></a>
### lens_flare

dimension `optics` | unit `shot` | claim `estimated` | verified

Artefacts produced when a bright source hits the lens: streaks, ghosts, starbursts.

**Aliases:** flare; anamorphic flare; starbursts

**Observable cues**
- Streaks or polygonal ghosts aligned with a bright source
- Raised blacks around the source

**Measurement hints**
- Clipped source in or near frame (color.light_source_in_frame) plus line or ghost artefacts on the axis through frame centre

**Not to be confused with**
- [`halation`](#halation): Halation is a red-orange glow hugging bright edges, not streaks or ghosts.
- [`atmospheric_haze`](#atmospheric_haze): Haze and light beams live in the air, not in the lens; they do not form ghosts on the axis through frame centre.

**Prompt phrase:** "Subtle lens flare from the bright backlight."

**Bindings**
- effectcraft-0.17: exact - add_effect ec.generate.lensflare
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0108

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [VFX in 4K](https://higgsfield.ai/blog/vfx_4k) (accessed 2026-11-01)

---

<a id="halation"></a>
### halation

dimension `optics` | unit `shot` | claim `estimated` | verified

A warm glowing halo bleeding around bright highlights, characteristic of film emulation.

**Aliases:** Halation; halation bloom; Halation Vintage

**Observable cues**
- Red-orange glow around bright edges and practicals

**Measurement hints**
- Positive frames.highlight_bloom with a warm (a*, b* > 0) halo around clipped areas

**Not to be confused with**
- [`diffusion`](#diffusion): Diffusion glow is neutral and softens the whole frame.
- [`lens_flare`](#lens_flare): Flare forms streaks or ghosts along an axis.

**Prompt phrase:** "Soft film halation around the highlights."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.stylize.glow
- ffmpeg: approx - split,curves,gblur,blend
- higgsfield-cinema-4.0: approx - camera_lens_id=<Halation Vintage>
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0109

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="vignetting"></a>
### vignetting

dimension `optics` | unit `shot` | claim `measured` | verified

The image darkens (or softens) toward the corners.

**Aliases:** vignette

**Observable cues**
- Corners darker than centre

**Measurement hints**
- frames.edge_falloff_luma: corner L* lower than centre L* by more than ~8 units consistently across shots

**Not to be confused with**
- [`low_key`](#low_key): Low-key darkness follows the light design, not a radial falloff.
- [`high_contrast`](#high_contrast): Global contrast does not depend on distance from the centre.

**Prompt phrase:** "Gentle vignette darkening the corners."

**Bindings**
- effectcraft-0.17: exact - add_effect ec.stylize.ccvignette
- ffmpeg: exact - vignette
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0111

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Cinematic Headphones · Ultra-Realistic Ads](https://higgsfield.ai/blog/cinematic_headphones) (accessed 2026-11-01)

---

<a id="motion_blur"></a>
### motion_blur

dimension `optics` | unit `shot` | claim `estimated` | verified

Streaking of moving elements during exposure; long-shutter looks exaggerate it.

**Aliases:** Low Shutter; natural motion blur; long exposure; 180-degree shutter

**Observable cues**
- Moving objects smeared along their direction while static ones stay sharp

**Measurement hints**
- motion.motion_blur_streak aligned with local flow direction; streak length proportional to speed

**Not to be confused with**
- [`shallow_depth_of_field`](#shallow_depth_of_field): Defocus blur is isotropic and tied to depth.
- [`ghosting`](#ghosting): Ghosting shows discrete double contours rather than a continuous smear.

**Prompt phrase:** "Natural motion blur on the moving elements."

**Bindings**
- effectcraft-0.17: approx - comp.settings
- ffmpeg: approx - tmix
- higgsfield-camera-controls: approx - preset 'Low Shutter'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0115, HF-0113, HF-0445

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Motion preset: Low Shutter](https://higgsfield.ai/motion/f7949a2f-2bcd-459a-96c0-80eb222abcdc) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="diffusion"></a>
### diffusion

dimension `optics` | unit `shot` | claim `estimated` | verified

Optical softening and highlight glow across the whole frame (diffusion filter or mist look).

**Aliases:** diffusion filter; Pro-Mist look; soft focus

**Observable cues**
- Highlights bloom softly; lowered micro-contrast everywhere

**Measurement hints**
- Global reduction of frames.sharpness_laplacian_var plus neutral frames.highlight_bloom

**Not to be confused with**
- [`shallow_depth_of_field`](#shallow_depth_of_field): Shallow DOF keeps the focus plane crisp.
- [`halation`](#halation): Halation is warm-coloured and edge-hugging.

**Prompt phrase:** "Soft diffusion filter with gentle highlight glow."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.stylize.glow
- ffmpeg: approx - split,gblur,blend
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0144

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="dim-light-direction"></a>
## light.direction

Temporal unit `shot`, cardinality `single`.

Apparent direction from which the key light reaches the principal subject. Screen side is a qualifier. Never infer exact positions, Kelvin, or lux from pixels.

- Qualifier `screen_side`: screen_left, screen_right, center, unclear. Side of the frame the key appears to come from.

Measurement keys: `color.light_face_luma_asymmetry`, `color.shadow_edge_width`, `color.light_contrast_ratio`, `color.specular_highlights`, `color.contact_shadow`

<a id="front_light"></a>
### front_light

dimension `light.direction` | unit `shot` | claim `estimated` | **unverified**

The key comes from near the camera axis: few visible shadows, flat modelling.

**Aliases:** frontal light; on-axis light

**Observable cues**
- Shadows fall behind the subject; both sides of a face equally lit

**Measurement hints**
- color.light_face_luma_asymmetry ~0; catchlights centred in the eyes

**Not to be confused with**
- [`flat_light`](#flat_light): Flat light is about quality (no modelling from any direction); front light names a direction.

**Prompt phrase:** "Soft frontal key light from near the camera."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Direction vocabulary normalised under the documented 'Light direction' entry (HF-0142); 'front light' itself is not verbatim in the re-read guides.

**Dictionary:** HF-0142

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Consistent Characters and Locations](https://higgsfield.ai/blog/consistent-characters-locations) (accessed 2026-11-01)

---

<a id="side_light"></a>
### side_light

dimension `light.direction` | unit `shot` | claim `estimated` | verified

The key arrives from the subject's side (about 90 degrees), splitting it into lit and shadow halves.

**Aliases:** side light; soft side light; soft side key; raking light

**Observable cues**
- Strong lit/shadow split along the subject's centre line
- Texture raked and emphasised

**Measurement hints**
- High color.light_face_luma_asymmetry (> ~0.4); long shadows parallel to the frame

**Not to be confused with**
- A 45-degree key keeps most of the face lit; side light leaves half in shadow.
- [`window_light`](#window_light): Window light is a scheme; it often produces soft side light.

**Prompt phrase:** "Soft side light from camera-left raking across the surface."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** 'Soft side light' is used verbatim in the Higgsfield 'look filmed' guide (Window preset). 'soft_side_key' was not found in any consulted guide and is treated as an alias of side_light + soft_light.

**Dictionary:** HF-0124

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="top_light"></a>
### top_light

dimension `light.direction` | unit `shot` | claim `estimated` | verified

The key comes from overhead, casting shadows straight down (eye sockets, under plates).

**Aliases:** light from above; overhead light

**Observable cues**
- Dark eye sockets; shadows directly beneath objects

**Measurement hints**
- Top regions brighter than lower regions on the subject; short contact shadows directly below

**Not to be confused with**
- [`overhead_fall`](#overhead_fall): Overhead fall is the named Higgsfield scheme; top_light is the bare direction.

**Prompt phrase:** "Top light from directly above."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0125

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="backlight"></a>
### backlight

dimension `light.direction` | unit `shot` | claim `estimated` | verified

The key comes from behind the subject relative to the camera, lighting edges and leaving the front darker.

**Aliases:** back light; backlit; light from behind

**Observable cues**
- Bright outline around the subject; front side darker than background

**Measurement hints**
- Subject interior L* below background L* with a bright edge (color.rim_edge_luma high)

**Not to be confused with**
- [`rim_light`](#rim_light): A rim can be a secondary light added to a front key; backlight is the key itself.
- [`contre_jour`](#contre_jour): Contre-jour shoots into the source, which is visible or flaring in frame.

**Prompt phrase:** "Strong backlight outlining the subject."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0123

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="dim-light-quality"></a>
## light.quality

Temporal unit `shot`, cardinality `single`.

Hardness of the dominant light measured at shadow edges, independent of direction and of contrast. Soft light can still be high contrast.

Measurement keys: `color.shadow_edge_width`, `color.specular_highlights`, `color.light_contrast_ratio`, `frames.L_std`

<a id="soft_light"></a>
### soft_light

dimension `light.quality` | unit `shot` | claim `estimated` | verified

Light from a large source relative to the subject: gradual shadow edges.

**Aliases:** soft light; diffused light; soft shadows; softbox light

**Observable cues**
- Shadow transitions spread over many pixels; no crisp cast-shadow outlines

**Measurement hints**
- Wide color.shadow_edge_width (penumbra > ~2% of subject width)

**Not to be confused with**
- [`flat_light`](#flat_light): Soft light still models form with a gradient; flat light has almost no gradient.
- [`low_contrast`](#low_contrast): Edge softness is independent of the lit/shadow ratio.

**Prompt phrase:** "Soft, diffused key light with gentle shadow transitions."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0126, HF-0128, HF-0138

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)
- [Cinematic Headphones · Ultra-Realistic Ads](https://higgsfield.ai/blog/cinematic_headphones) (accessed 2026-11-01)
- [Cinematic Car Commercial](https://higgsfield.ai/blog/ai-car-commercial-youtube-guide) (accessed 2026-11-01)

---

<a id="hard_light"></a>
### hard_light

dimension `light.quality` | unit `shot` | claim `estimated` | verified

Light from a small or distant source: crisp, well-defined shadow edges and sharp specular highlights.

**Aliases:** hard light; crisp shadows; hard key; direct sun

**Observable cues**
- Cast shadows with sharp outlines; small bright specular points

**Measurement hints**
- Narrow color.shadow_edge_width; compact intense color.specular_highlights

**Not to be confused with**
- [`high_contrast`](#high_contrast): High contrast can come from soft light with no fill.

**Prompt phrase:** "Hard directional light with crisp shadows."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0127

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Cinematic Car Commercial](https://higgsfield.ai/blog/ai-car-commercial-youtube-guide) (accessed 2026-11-01)

---

<a id="flat_light"></a>
### flat_light

dimension `light.quality` | unit `shot` | claim `estimated` | **unverified**

Shadowless, even illumination that barely models form (overcast, ring light, heavy fill).

**Aliases:** flat lighting; even light; shadowless

**Observable cues**
- Almost no shadows on the subject; surfaces read with little depth

**Measurement hints**
- Very low luma gradient across the subject and low color.light_contrast_ratio

**Not to be confused with**
- [`soft_light`](#soft_light): Soft light still shows a clear direction.
- [`high_key`](#high_key): High key is about overall brightness, not modelling.

**Prompt phrase:** "Even, shadowless light."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Commonly used; 'flat lighting' not found verbatim in the re-read Higgsfield pages.

**Sources**
- [Kling 4.0 and 3.0 Prompt Guide](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="dim-light-key"></a>
## light.key

Temporal unit `shot`, cardinality `single`.

Tonal key: the overall distribution of tones in the lit scene (bright, middle or dark), measured on L* histograms per region.

Measurement keys: `frames.L_mean`, `frames.L_hist16`, `color.region_L_percentiles`, `frames.clip_highlights`, `frames.clip_shadows`

<a id="high_key"></a>
### high_key

dimension `light.key` | unit `shot` | claim `measured` | **unverified**

Predominantly bright tones with light shadows and restrained contrast; not careless overexposure.

**Aliases:** high-key; bright and airy

**Observable cues**
- Mostly white or pastel surfaces; shadows light grey

**Measurement hints**
- L* median > ~65 and p10 > ~35 in the main regions without large clipped areas

**Not to be confused with**
- Overexposure loses detail in clipped regions (frames.clip_highlights high); high key keeps highlight detail.

**Prompt phrase:** "High-key lighting, bright and airy."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Only a manufacturer photography source (Fujifilm) was found; no official Higgsfield guide uses 'high-key' (searched 2026-11-01).

**Dictionary:** TX-0015

**Sources**
- [Fujifilm: High-Key and Low-Key Photography](https://www.fujifilm-x.com/en-gb/learning-centre/mastering-high-key-and-low-key-photography/) (accessed 2026-11-01)

---

<a id="mid_key"></a>
### mid_key

dimension `light.key` | unit `shot` | claim `measured` | **unverified**

A balanced tonal distribution centred on middle grey with both highlights and shadows present.

**Aliases:** normal key; neutral exposure

**Observable cues**
- Normal exposure; full but not extreme range

**Measurement hints**
- L* median ~35-65 with balanced histogram tails

**Not to be confused with**
- [`high_key`](#high_key): High key shifts the whole histogram up.
- [`low_key`](#low_key): Low key shifts it down.

**Prompt phrase:** "Balanced, naturally exposed lighting."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris completion of the high/low key pair; 'neutral exposure' is the closest documented term.

**Dictionary:** HF-0162

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="low_key"></a>
### low_key

dimension `light.key` | unit `shot` | claim `measured` | verified

Predominantly dark tones with selected illuminated details; not merely underexposure.

**Aliases:** low-key

**Observable cues**
- Large dark areas with pools of light on the subject

**Measurement hints**
- L* median < ~35 with a bright subject region well above the scene median

**Not to be confused with**
- [`crushed_blacks`](#crushed_blacks): Crushed blacks is a grading defect or style of lost shadow detail, possible in any key.
- [`silhouette_lighting`](#silhouette_lighting): Silhouette keeps the subject dark against a bright background.

**Related:** can_realize [`chiaroscuro`](#chiaroscuro)

**Prompt phrase:** "Low-key lighting with pools of light in darkness."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** TX-0016

**Sources**
- [Fujifilm: High-Key and Low-Key Photography](https://www.fujifilm-x.com/en-gb/learning-centre/mastering-high-key-and-low-key-photography/) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="dim-light-scheme"></a>
## light.scheme

Temporal unit `shot`, cardinality `multi`.

Named lighting setups. Six names come verbatim from the Higgsfield Cinema Studio lighting presets (Soft cross, Contre jour, Overhead fall, Window, Practicals, Silhouette); the others are common light roles. A scheme is a pattern recognised from direction, quality and source cues together, so the default claim is interpreted.

Measurement keys: `color.light_face_luma_asymmetry`, `color.shadow_edge_width`, `color.light_contrast_ratio`, `color.rim_edge_luma`, `color.specular_highlights`, `color.contact_shadow`, `color.light_source_in_frame`, `sheets.keyframes`

<a id="soft_cross"></a>
### soft_cross

dimension `light.scheme` | unit `shot` | claim `interpreted` | verified

Two soft sources from roughly opposite sides crossing on the subject, giving modelling from both sides with soft shadows.

**Aliases:** Soft cross; Soft Cross; light from two sides

**Observable cues**
- Two shadow directions, both soft
- Highlights on both edges of the subject

**Measurement hints**
- Two opposing luma gradients on the subject; wide color.shadow_edge_width

**Not to be confused with**
- [`rim_light`](#rim_light): A rim lights only the edge from behind.
- [`flat_light`](#flat_light): Flat light has no directional gradients at all.

**Prompt phrase:** "Soft cross lighting from two opposite sides."

**Bindings**
- higgsfield-cinema-3.5: exact - light_scheme=soft_cross
- higgsfield-cinema-4.0: exact - light=preset, light_id=None
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0361

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="contre_jour"></a>
### contre_jour

dimension `light.scheme` | unit `shot` | claim `interpreted` | verified

Shooting into the light: the source sits behind the subject and is visible or flaring in frame.

**Aliases:** Contre jour; contre-jour; into the sun

**Observable cues**
- Bright source (sun, window) in frame behind the subject; flare or haze; dark subject front

**Measurement hints**
- color.light_source_in_frame true with subject front darker than background; often lens_flare

**Not to be confused with**
- [`backlight`](#backlight): Backlight can come from an unseen source behind the subject.
- [`silhouette_lighting`](#silhouette_lighting): Silhouette suppresses all front detail.

**Prompt phrase:** "Contre-jour, shooting into the low sun behind the subject."

**Bindings**
- higgsfield-cinema-3.5: exact - light_scheme=contre_jour
- higgsfield-cinema-4.0: exact - light=preset, light_id=None
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0123, HF-0361

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="overhead_fall"></a>
### overhead_fall

dimension `light.scheme` | unit `shot` | claim `interpreted` | verified

A single overhead source falling down onto the subject with darkness falling off around it.

**Aliases:** Overhead fall; overhead cone; narrow overhead cone

**Observable cues**
- Pool of light from above; surroundings fall to dark

**Measurement hints**
- Top-lit subject with strong radial falloff of L* away from it

**Not to be confused with**
- [`top_light`](#top_light): Top light is the direction only; overhead fall adds the falloff pool.
- [`practical_light`](#practical_light): Practicals are visible fixtures; overhead fall may be motivated by one.

**Prompt phrase:** "A single overhead light falling onto the subject, darkness around."

**Bindings**
- higgsfield-cinema-3.5: exact - light_scheme=overhead_fall
- higgsfield-cinema-4.0: exact - light=preset, light_id=None
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0361

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="window_light"></a>
### window_light

dimension `light.scheme` | unit `shot` | claim `interpreted` | verified

Soft directional daylight that appears to come through a window, usually from the side.

**Aliases:** Window; window light; soft window light

**Observable cues**
- Soft side light with a cool or neutral tone; possible window-frame shadow pattern

**Measurement hints**
- Side-dominant luma gradient with wide color.shadow_edge_width; cooler b* on the lit side

**Not to be confused with**
- A studio softbox looks similar but lacks window motivation and daylight colour.
- [`side_light`](#side_light): side_light is the bare direction; window_light is the motivated scheme.

**Prompt phrase:** "Soft window light from the side."

**Bindings**
- higgsfield-cinema-3.5: exact - light_scheme=window
- higgsfield-cinema-4.0: exact - light=preset, light_id=None
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0132, HF-0361

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="practical_light"></a>
### practical_light

dimension `light.scheme` | unit `shot` | claim `interpreted` | verified

Visible fixtures inside the frame (lamps, neon, candles, screens) provide or motivate the light.

**Aliases:** Practicals; practicals; practical glow; motivated light

**Observable cues**
- Lit fixtures visible in frame with matching light falling on nearby surfaces

**Measurement hints**
- Bright small sources in frame (color.light_source_in_frame) with local falloff on adjacent surfaces

**Not to be confused with**
- [`lens_flare`](#lens_flare): Flare is a lens artefact, not a fixture.
- [`hyper_neon`](#hyper_neon): hyper_neon is the colour grade; practical_light is the light scheme.

**Prompt phrase:** "Lit by warm practical lamps visible in the frame."

**Bindings**
- higgsfield-cinema-3.5: exact - light_scheme=practicals
- higgsfield-cinema-4.0: exact - light=preset, light_id=None
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0133, HF-0129, HF-0361

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="silhouette_lighting"></a>
### silhouette_lighting

dimension `light.scheme` | unit `shot` | claim `interpreted` | verified

The background is lit and the subject is not, so the subject reads as a dark shape without internal detail.

**Aliases:** Silhouette; silhouette; rim-lit silhouette

**Observable cues**
- Dark subject with a crisp outline against a bright background

**Measurement hints**
- Subject mask L* far below background L* with little internal texture (low local variance)

**Not to be confused with**
- [`backlight`](#backlight): Backlit subjects can keep visible front detail.
- [`low_key`](#low_key): Low key lights the subject and darkens the background.

**Related:** realizes [`silhouette`](#silhouette)

**Prompt phrase:** "The subject in silhouette against a bright background."

**Bindings**
- higgsfield-cinema-3.5: exact - light_scheme=silhouette
- higgsfield-cinema-4.0: exact - light=preset, light_id=None
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Higgsfield label is 'Silhouette'; suffixed id because the Iris composition technique 'silhouette' keeps the bare id.

**Dictionary:** HF-0361

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: How to Make AI Video Look Filmed (re-read 2026-11-01)](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="rim_light"></a>
### rim_light

dimension `light.scheme` | unit `shot` | claim `estimated` | verified

A light behind or beside the subject that draws a bright contour along its edge, separating it from the background.

**Aliases:** rim light; rim; edge light; kicker

**Observable cues**
- Thin bright edge along hair, shoulders, glass or food contours

**Measurement hints**
- High color.rim_edge_luma: a band of pixels along the subject boundary brighter than both interior and background

**Not to be confused with**
- [`backlight`](#backlight): Backlight is the key itself from behind; a rim can accompany a front key.
- [`halation`](#halation): Halation is a glow around highlights, not a lit contour.

**Related:** realizes [`rimlight`](#rimlight)

**Prompt phrase:** "A crisp rim light separating the subject from the background."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0122

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="dim-color-grade_family"></a>
## color.grade_family

Temporal unit `shot`, cardinality `single`, region-scoped.

Overall colour treatment family. Measured per region and then summarised; a grade family is a pattern across shadows, mids and highlights, so the default claim is estimated. Eight ids align with the cinematic_studio_video_3_5.color_grading enum.

Measurement keys: `color.region_palette`, `color.region_ab_mean`, `color.region_saturation`, `color.region_L_percentiles`, `color.region_shadow_hue`, `color.region_highlight_hue`, `color.region_deltaE_master`, `color.region_deltaE_neighbor`, `frames.sat_mean`, `frames.contrast_p5_p95`

<a id="naturalistic_clean"></a>
### naturalistic_clean

dimension `color.grade_family` | unit `shot` | claim `estimated` | verified | regions `background`, `food`, `product`, `skin`, `whole_frame`

A neutral, faithful grade: accurate whites, natural skin and food colour, moderate contrast.

**Aliases:** Naturalistic Clean; neutral documentary grade; clean saturated color science

**Observable cues**
- Whites read white; skin and food look true to life

**Measurement hints**
- Neutral regions have |a*|,|b*| < ~3; saturation and contrast in mid ranges

**Not to be confused with**
- [`bleached_warm`](#bleached_warm): Bleached warm lifts warmth and lowers saturation.

**Prompt phrase:** "Clean naturalistic colour grade with true-to-life colours."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.lumetri
- higgsfield-cinema-3.5: exact - color_grading=naturalistic_clean
- higgsfield-cinema-4.0: approx - color_palette=<Naturalistic Clean>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Enum label from the MCP catalog; no published definition. The definition here is descriptive.

**Dictionary:** HF-0147

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [HEX Color Control with Soul](https://higgsfield.ai/blog/hex-codes-ai-image-generation-color-control-soul) (accessed 2026-11-01)

---

<a id="bleached_warm"></a>
### bleached_warm

dimension `color.grade_family` | unit `shot` | claim `estimated` | **unverified** | regions `background`, `food`, `product`, `skin`, `whole_frame`

A warm grade with reduced saturation and lifted, creamy highlights.

**Aliases:** Bleached Warm

**Observable cues**
- Warm overall cast with washed, sun-faded colours

**Measurement hints**
- Positive b* shift in highlights and mids, saturation below scene norm, highlights lifted

**Not to be confused with**
- [`naturalistic_clean`](#naturalistic_clean): Clean keeps neutral whites.
- [`bleach_bypass`](#bleach_bypass): Bleach bypass is desaturated and high contrast with cool or neutral tone.

**Prompt phrase:** "Sun-bleached warm grade with soft, faded colours."

**Bindings**
- higgsfield-cinema-3.5: exact - color_grading=bleached_warm
- higgsfield-cinema-4.0: approx - color_palette=<Bleached Warm>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Enum value of cinematic_studio_video_3_5.color_grading (MCP catalog 2026-11-01); visual definition unpublished.

---

<a id="teal_orange"></a>
### teal_orange

dimension `color.grade_family` | unit `shot` | claim `estimated` | verified | regions `background`, `food`, `product`, `skin`, `whole_frame`

Complementary grade pushing shadows and backgrounds toward teal and skin or warm objects toward orange.

**Aliases:** Teal Orange Epic; teal and orange; teal-and-orange; cyan and amber

**Observable cues**
- Cyan-green shadows or backgrounds with warm subjects

**Measurement hints**
- Shadow hue (color.region_shadow_hue) in teal range (~180-200 deg) and skin/food a*,b* warm; bimodal hue histogram

**Not to be confused with**
- [`cold_steel`](#cold_steel): Cold steel is cool overall without warm subject accents.

**Prompt phrase:** "Teal and orange colour grade."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.colorbalance
- ffmpeg: approx - colorbalance
- higgsfield-cinema-3.5: exact - color_grading=teal_orange_epic
- higgsfield-cinema-4.0: approx - color_palette=<Teal Orange Epic>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0164

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="cold_steel"></a>
### cold_steel

dimension `color.grade_family` | unit `shot` | claim `estimated` | verified | regions `background`, `food`, `product`, `skin`, `whole_frame`

A cool, desaturated blue-grey grade with steely mids.

**Aliases:** Cold Steel; cold steel-blue; cold cinematic grade

**Observable cues**
- Blue-grey overall cast; muted colours

**Measurement hints**
- Negative b* across regions with low saturation

**Not to be confused with**
- [`teal_orange`](#teal_orange): Teal-orange keeps warm subjects.
- [`cool`](#cool): cool is a temperature reading; cold_steel is a full grade family.

**Prompt phrase:** "Cold steel-blue grade with desaturated mids."

**Bindings**
- higgsfield-cinema-3.5: exact - color_grading=cold_steel
- higgsfield-cinema-4.0: approx - color_palette=<Cold Steel>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="bleach_bypass"></a>
### bleach_bypass

dimension `color.grade_family` | unit `shot` | claim `estimated` | **unverified** | regions `background`, `food`, `product`, `skin`, `whole_frame`

A desaturated, high-contrast look with silvery highlights and dense shadows.

**Aliases:** Bleach Bypass; skip bleach

**Observable cues**
- Muted colours, harsh contrast, metallic sheen

**Measurement hints**
- Low saturation together with high frames.contrast_p5_p95

**Not to be confused with**
- [`black_and_white`](#black_and_white): Black and white removes all colour.
- [`bleached_warm`](#bleached_warm): Bleached warm is soft and warm, not harsh.

**Prompt phrase:** "Bleach bypass look, desaturated and high contrast."

**Bindings**
- ffmpeg: approx - eq
- higgsfield-cinema-3.5: exact - color_grading=bleach_bypass
- higgsfield-cinema-4.0: approx - color_palette=<Bleach Bypass>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Enum value of cinematic_studio_video_3_5.color_grading; Higgsfield publishes no definition.

---

<a id="black_and_white"></a>
### black_and_white

dimension `color.grade_family` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Monochrome image without chroma.

**Aliases:** Classic BW; monochrome; silver-gelatin black and white

**Observable cues**
- No colour anywhere

**Measurement hints**
- frames.sat_mean ~0 and |a*|,|b*| < ~2 in all regions

**Not to be confused with**
- [`muted`](#muted): Muted keeps some colour.

**Prompt phrase:** "Classic black and white."

**Bindings**
- effectcraft-0.17: exact - add_effect ec.color.blackwhite
- ffmpeg: exact - hue
- higgsfield-cinema-3.5: exact - color_grading=classic_bw
- higgsfield-cinema-4.0: approx - color_palette=<Classic BW>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="hyper_neon"></a>
### hyper_neon

dimension `color.grade_family` | unit `shot` | claim `estimated` | verified | regions `background`, `food`, `product`, `skin`, `whole_frame`

A saturated night grade dominated by magenta, cyan and electric blue light.

**Aliases:** Hyper Neon; neon; neon glow

**Observable cues**
- Glowing saturated magenta/cyan sources and reflections

**Measurement hints**
- High saturation p90 with hue peaks in magenta and cyan ranges; dark mids

**Not to be confused with**
- [`practical_light`](#practical_light): Practicals are the light scheme; hyper_neon is the grade.
- [`saturated`](#saturated): saturated is a level, not a family.

**Prompt phrase:** "Hyper-saturated neon night grade."

**Bindings**
- higgsfield-cinema-3.5: exact - color_grading=hyper_neon
- higgsfield-cinema-4.0: approx - color_palette=<Hyper Neon>
- prompt only on: higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0137

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)

---

<a id="filmic_print"></a>
### filmic_print

dimension `color.grade_family` | unit `shot` | claim `estimated` | verified | regions `background`, `food`, `product`, `skin`, `whole_frame`

A grade emulating photographic film print: soft highlight roll-off, gentle contrast curve, slightly lifted or milky shadows.

**Aliases:** filmic print grade; Film Colors; milky filmic floor; 35mm film look

**Observable cues**
- Highlights roll off gently; shadows slightly milky; organic colour

**Measurement hints**
- S-shaped tone curve inferred from color.region_L_percentiles, highlights rarely clipped, mild lifted blacks

**Not to be confused with**
- [`naturalistic_clean`](#naturalistic_clean): Clean digital grades clip harder and keep pure blacks.

**Prompt phrase:** "Filmic print grade with soft highlight roll-off."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.utility.applylut
- ffmpeg: approx - lut3d
- higgsfield-cinema-4.0: approx - camera_model_id=<35mm Film>
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0161, HF-0117, HF-0110, HF-0367

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="dim-color-palette_role"></a>
## color.palette_role

Temporal unit `shot`, cardinality `multi`, region-scoped.

Role of a colour cluster within a region's palette (60:30:10 roles). Claims attach a swatch (Lab and HEX) and an area share.

Measurement keys: `color.region_palette`, `color.region_hue_histogram`

<a id="dominant_color"></a>
### dominant_color

dimension `color.palette_role` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

The colour cluster covering the largest share of the region (roughly 60%).

**Aliases:** dominant; base colour

**Observable cues**
- Most visible colour of the region

**Measurement hints**
- Largest area share in color.region_palette (typically > 45%)

**Not to be confused with**
- [`accent_color`](#accent_color): An accent is small but salient.

**Prompt phrase:** "A palette dominated by soft sage green."

**Dictionary:** HF-0156, HF-0157

**Sources**
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="secondary_color"></a>
### secondary_color

dimension `color.palette_role` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

The supporting colour cluster (roughly 30%).

**Aliases:** secondary; supporting colour

**Observable cues**
- Second most visible colour

**Measurement hints**
- Second-largest area share in color.region_palette

**Not to be confused with**
- [`dominant_color`](#dominant_color): The dominant takes the largest share.

**Prompt phrase:** "With warm cream as the secondary colour."

**Dictionary:** HF-0156

**Sources**
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="accent_color"></a>
### accent_color

dimension `color.palette_role` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

A small, high-contrast or high-saturation cluster that attracts attention (roughly 10% or less).

**Aliases:** accent; pop colour

**Observable cues**
- Small vivid spots: a red garnish, a CTA button

**Measurement hints**
- Area share < ~12% with a large hue or saturation distance from the dominant (deltaE > ~25)

**Not to be confused with**
- [`popout`](#popout): popout is the Iris technique the accent may realise; accent_color is the measured palette role.

**Related:** can_realize [`popout`](#popout)

**Prompt phrase:** "A single vivid red accent."

**Dictionary:** HF-0156

**Sources**
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="dim-color-temperature"></a>
## color.temperature

Temporal unit `shot`, cardinality `single`, region-scoped.

Relative warm/cool reading of a region from its a*b* balance. Never a Kelvin claim (Kelvin only as designed).

Measurement keys: `color.region_ab_mean`, `frames.b_mean`, `color.region_shadow_hue`, `color.region_highlight_hue`, `frames.a_mean`

<a id="warm"></a>
### warm

dimension `color.temperature` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

The region is biased toward yellow-orange.

**Aliases:** warm cast; warm tone; golden

**Observable cues**
- Whites look cream or amber

**Measurement hints**
- Region mean b* > ~+6 on neutral references (or relative to the master reference)

**Not to be confused with**
- [`bleached_warm`](#bleached_warm): A warm temperature alone does not imply the bleached grade.

**Prompt phrase:** "Warm colour temperature."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.photofilter
- ffmpeg: approx - colortemperature
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0153, HF-0136

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [HEX Color Control with Soul](https://higgsfield.ai/blog/hex-codes-ai-image-generation-color-control-soul) (accessed 2026-11-01)
- [Nano Banana Pro Expert Use Cases](https://higgsfield.ai/blog/Nano-Banana-Pro-Expert-Use-Cases) (accessed 2026-11-01)

---

<a id="neutral_balance"></a>
### neutral_balance

dimension `color.temperature` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Neutral surfaces read neutral: no visible warm or cool cast.

**Aliases:** neutral white balance; neutral

**Observable cues**
- Whites and greys look neutral

**Measurement hints**
- |a*| and |b*| < ~3 on neutral references

**Not to be confused with**
- [`mixed_temperature`](#mixed_temperature): Mixed has warm and cool zones that average to neutral.

**Prompt phrase:** "Neutral white balance."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0151

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Seedance 4K Film Breakdown](https://higgsfield.ai/blog/seedance4k-breakdown) (accessed 2026-11-01)

---

<a id="cool"></a>
### cool

dimension `color.temperature` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

The region is biased toward blue-cyan.

**Aliases:** cool cast; cool tone; blue hour

**Observable cues**
- Whites look bluish

**Measurement hints**
- Region mean b* < ~-6 on neutral references

**Not to be confused with**
- [`cold_steel`](#cold_steel): Cold steel is a full grade family, not just a cool cast.

**Prompt phrase:** "Cool colour temperature."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.photofilter
- ffmpeg: approx - colortemperature
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0153, HF-0135

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [HEX Color Control with Soul](https://higgsfield.ai/blog/hex-codes-ai-image-generation-color-control-soul) (accessed 2026-11-01)
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="mixed_temperature"></a>
### mixed_temperature

dimension `color.temperature` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Clearly warm and clearly cool sources coexist in different zones of the region or frame.

**Aliases:** warm-cold contrast; mixed white balance

**Observable cues**
- Warm practical next to cool window light

**Measurement hints**
- Spatial b* distribution bimodal (warm and cool clusters each > ~15% area)

**Not to be confused with**
- [`teal_orange`](#teal_orange): Teal-orange is a deliberate grade; mixed temperature can be the raw light.

**Prompt phrase:** "Warm interior light mixed with cool daylight."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="dim-color-saturation_level"></a>
## color.saturation_level

Temporal unit `shot`, cardinality `single`, region-scoped.

Chroma intensity of a region relative to the scene and to the master reference.

Measurement keys: `color.region_saturation`, `frames.sat_mean`, `frames.sat_p90`, `frames.colorfulness`

<a id="muted"></a>
### muted

dimension `color.saturation_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Reduced colour intensity; colours look soft or greyed.

**Aliases:** desaturated; muted; pastel

**Observable cues**
- Pastel or dusty colours

**Measurement hints**
- Region saturation p50 below ~0.25 (HSV) or chroma C* < ~20 on coloured surfaces

**Not to be confused with**
- [`black_and_white`](#black_and_white): Black and white has no chroma at all.

**Prompt phrase:** "Muted, desaturated colours."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.huesaturation
- ffmpeg: exact - eq
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0154

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="natural_saturation"></a>
### natural_saturation

dimension `color.saturation_level` | unit `shot` | claim `measured` | **unverified** | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Chroma consistent with the real surfaces under neutral light.

**Aliases:** natural colour

**Observable cues**
- Colours look plausible and true

**Measurement hints**
- Region saturation within the calibration band of the master reference

**Not to be confused with**
- [`saturated`](#saturated): Saturated pushes colour beyond natural.

**Prompt phrase:** "Natural, true-to-life saturation."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris completion of the muted/saturated pair.

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="saturated"></a>
### saturated

dimension `color.saturation_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Strong colour intensity; vivid but not clipping.

**Aliases:** vivid; saturated; color pop

**Observable cues**
- Vivid, punchy colours

**Measurement hints**
- Region saturation p90 > ~0.7 without channel clipping

**Not to be confused with**
- Hypersaturation clips channels and loses texture (QA concern, see color.region_saturation).

**Prompt phrase:** "Vivid, saturated colours."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.vibrance
- ffmpeg: exact - eq
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0155

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="dim-color-contrast_level"></a>
## color.contrast_level

Temporal unit `shot`, cardinality `multi`, region-scoped.

Tonal contrast of a region (one of low/medium/high) plus optional black-point flags.

- Mutually exclusive: low_contrast, medium_contrast, high_contrast

Measurement keys: `frames.contrast_rms`, `frames.contrast_p5_p95`, `color.region_L_percentiles`, `frames.clip_shadows`, `frames.clip_highlights`, `frames.L_std`

<a id="low_contrast"></a>
### low_contrast

dimension `color.contrast_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Compressed tonal range: few deep shadows or bright highlights.

**Aliases:** low contrast; flat contrast

**Observable cues**
- Greyish blacks and dull whites

**Measurement hints**
- L* p95 - p5 < ~45

**Not to be confused with**
- [`lifted_blacks`](#lifted_blacks): Lifted blacks raises only the floor; contrast elsewhere can stay high.

**Prompt phrase:** "Low-contrast, soft tonal range."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.brightnesscontrast
- ffmpeg: exact - eq
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="medium_contrast"></a>
### medium_contrast

dimension `color.contrast_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

A full tonal range without extreme compression or expansion.

**Aliases:** natural contrast

**Observable cues**
- Clear blacks and whites with detail in both

**Measurement hints**
- L* p95 - p5 ~45-75

**Not to be confused with**
- [`high_contrast`](#high_contrast): High contrast pushes tails apart.

**Prompt phrase:** "Natural contrast."

**Bindings**
- ffmpeg: approx - curves
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="high_contrast"></a>
### high_contrast

dimension `color.contrast_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Expanded tonal range with dense shadows and bright highlights.

**Aliases:** high-contrast; filmic contrast; deep blacks

**Observable cues**
- Deep blacks next to bright highlights

**Measurement hints**
- L* p95 - p5 > ~75

**Not to be confused with**
- [`hard_light`](#hard_light): Hard light is about shadow edges, not overall range.

**Prompt phrase:** "High contrast with deep blacks."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.curves
- ffmpeg: exact - eq
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0158

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Video Relight and Color Palette](https://higgsfield.ai/blog/video-relight-color-palette-higgsfield) (accessed 2026-11-01)

---

<a id="crushed_blacks"></a>
### crushed_blacks

dimension `color.contrast_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

Shadow detail compressed to a solid black floor.

**Aliases:** crushed blacks

**Observable cues**
- Shadows merge into featureless black

**Measurement hints**
- frames.clip_shadows share > ~3% of region with no texture variance

**Not to be confused with**
- [`low_key`](#low_key): Low key can keep shadow detail.

**Prompt phrase:** "Crushed, inky blacks."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.levels
- ffmpeg: exact - curves
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0159

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Kling 4.0 and 3.0 Prompt Guide](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="lifted_blacks"></a>
### lifted_blacks

dimension `color.contrast_level` | unit `shot` | claim `measured` | verified | regions `background`, `food`, `product`, `skin`, `ui`, `graphics`, `whole_frame`

The black point is raised so the darkest tones read as grey (faded or matte look).

**Aliases:** faded blacks; matte black; milky shadows

**Observable cues**
- No true black anywhere; milky shadows

**Measurement hints**
- Region L* p1 > ~12 while highlights remain bright

**Not to be confused with**
- [`low_contrast`](#low_contrast): Low contrast compresses both ends.

**Prompt phrase:** "Lifted, faded blacks."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.color.levels
- ffmpeg: exact - curves
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="dim-framing-placement"></a>
## framing.placement

Temporal unit `frame`, cardinality `multi`.

Measured placement of the principal subject in the frame grid; complements the interpretive Iris composition techniques.

Measurement keys: `motion.subject_grid_position`, `motion.subject_track`, `text.position_norm`

<a id="centered_composition"></a>
### centered_composition

dimension `framing.placement` | unit `frame` | claim `measured` | verified

The principal subject sits on or near the frame centre.

**Aliases:** centered; central framing

**Observable cues**
- Subject centroid near the centre

**Measurement hints**
- Subject centroid within ~0.1 of (0.5, 0.5) in normalised coordinates

**Not to be confused with**
- [`centralbias`](#centralbias): centralbias is the Iris attention technique; centered_composition is the measured placement.

**Related:** can_realize [`centralbias`](#centralbias)

**Prompt phrase:** "Subject centred in frame."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0051, HF-0052

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="rule_of_thirds"></a>
### rule_of_thirds

dimension `framing.placement` | unit `frame` | claim `measured` | verified

The principal subject or horizon sits near a thirds line or intersection.

**Aliases:** thirds

**Observable cues**
- Subject off-centre on a thirds intersection

**Measurement hints**
- Subject centroid within ~0.07 of a thirds line or intersection

**Not to be confused with**
- [`centered_composition`](#centered_composition): Centred subjects sit at 0.5, not 0.33 or 0.67.

**Prompt phrase:** "Subject placed on the left third."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0053

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="negative_space"></a>
### negative_space

dimension `framing.placement` | unit `frame` | claim `measured` | verified

A large empty, uniform area deliberately left around the subject, often reserved for text.

**Aliases:** empty space; looking room; headroom for text

**Observable cues**
- Large clean area (sky, wall, tabletop) next to the subject

**Measurement hints**
- A contiguous low-edge-density area > ~30% of the frame (frames.edge_density low)

**Not to be confused with**
- [`isolation`](#isolation): isolation is the Iris technique; negative_space is the measured empty area.

**Related:** can_realize [`isolation`](#isolation)

**Prompt phrase:** "Generous negative space above the subject for text."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0055

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="layered_depth"></a>
### layered_depth

dimension `framing.placement` | unit `frame` | claim `estimated` | verified

Distinct foreground, midground and background layers are visible and separated.

**Aliases:** foreground/midground/background; layered composition

**Observable cues**
- Foreground element, subject and background each readable

**Measurement hints**
- Three or more depth clusters (sharpness or parallax bands) in frames.sharpness_map_grid or motion.parallax_ratio

**Not to be confused with**
- [`deep_focus`](#deep_focus): Deep focus is about sharpness; layered depth is about distinct planes.

**Prompt phrase:** "Layered depth with a soft foreground element."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0049, HF-0050

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="dim-composition"></a>
## composition

Temporal unit `frame`, cardinality `multi`.

The 43 Iris visual techniques, classified by what the image does, not by what it shows. Ids are the original Iris ids. Evaluated on keyframes and contact sheets; most claims are interpreted and need a supporting sequence and a reviewer reason. An image usually shows one or two defining techniques plus supporting ones; untagged is a legitimate state. Where a cinematography term describes the same physical cue (rim_light, shallow_depth_of_field, silhouette_lighting), the Iris technique records the function and the other term records the measured appearance; they are linked with related_terms.

Measurement keys: `sheets.keyframes`, `color.region_palette`, `frames.edge_density`, `motion.subject_grid_position`, `motion.subject_scale_ratio`

<a id="chiaroscuro"></a>
### chiaroscuro

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `chiaroscuro`

Strong light-dark modelling inside the form that gives volume.

**Observable cues**
- Strong tonal gradient across the subject's surface; deep shadows inside the form

**Measurement hints**
- High luma variance inside the subject mask with a continuous gradient (not a flat dark shape)

**Not to be confused with**
- [`silhouette`](#silhouette): Silhouette suppresses internal detail; chiaroscuro models it.
- [`low_key`](#low_key): A black background alone is neither silhouette nor chiaroscuro.

**Related:** often_with [`low_key`](#low_key); often_with [`hard_light`](#hard_light)

**Prompt phrase:** "Dramatic chiaroscuro modelling the form in light and shadow."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="rimlight"></a>
### rimlight

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `rimlight`

An edge of light that separates the subject from the ground, used to make it stand apart.

**Observable cues**
- Bright contour around the subject against a darker ground

**Measurement hints**
- High color.rim_edge_luma along the subject boundary

**Not to be confused with**
- [`silhouette`](#silhouette): Silhouette darkens the subject interior; rim light only brightens the edge.

**Related:** realized_by [`rim_light`](#rim_light)

**Prompt phrase:** "A bright rim separating the subject from the dark background."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="complementary"></a>
### complementary

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `complementary`

Two opposed hue families placed against each other to sharpen separation.

**Observable cues**
- Two dominant hues roughly opposite on the colour wheel

**Measurement hints**
- Bimodal hue histogram with peaks ~150-210 degrees apart

**Not to be confused with**
- [`warmcool`](#warmcool): Warm/cool opposition can be non-complementary (orange vs blue-green is both; red vs blue is warm/cool but not complementary).

**Prompt phrase:** "Complementary colour contrast between subject and background."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="simultaneous"></a>
### simultaneous

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `simultaneous`

A colour or grey looks different because of the colour that surrounds it (simultaneous contrast).

**Observable cues**
- Same patch reads differently on two different grounds

**Measurement hints**
- Equal Lab values in two regions whose surrounds differ strongly

**Not to be confused with**
- [`complementary`](#complementary): Complementary is about two hues opposing; simultaneous is about context changing perception of one.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="warmcool"></a>
### warmcool

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `warmcool`

Warm and cool areas set apart to create separation or depth.

**Observable cues**
- Warm subject against a cool ground or vice versa

**Measurement hints**
- Region b* difference between subject and background > ~15

**Not to be confused with**
- [`mixed_temperature`](#mixed_temperature): mixed_temperature is the measured light condition; warmcool is the deliberate separating technique.

**Prompt phrase:** "Warm subject set against a cool background."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="satblock"></a>
### satblock

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `satblock`

Flat fields of strong colour meeting on hard edges, often with a third block inside one of them.

**Observable cues**
- Large flat saturated colour areas with crisp boundaries

**Measurement hints**
- Few large low-variance high-saturation regions in color.region_palette

**Not to be confused with**
- [`popout`](#popout): Pop-out is one small odd element; satblock is the structure of large flat fields.

**Prompt phrase:** "Bold flat blocks of saturated colour meeting on hard edges."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="silhouette"></a>
### silhouette

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `silhouette`

A recognisable shape whose internal detail is suppressed.

**Observable cues**
- Dark shape with a readable outline and no internal texture

**Measurement hints**
- Subject mask uniform and dark vs bright ground

**Not to be confused with**
- [`chiaroscuro`](#chiaroscuro): Chiaroscuro keeps internal modelling.
- [`low_key`](#low_key): A black background alone is neither silhouette nor chiaroscuro.

**Related:** realized_by [`silhouette_lighting`](#silhouette_lighting)

**Prompt phrase:** "The subject as a crisp dark silhouette."

**Bindings**
- higgsfield-cinema-3.5: approx - light_scheme=silhouette
- prompt only on: higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="dof"></a>
### dof

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `dof`

Selective focus: the sharp element stands apart from blurred surroundings.

**Observable cues**
- One sharp element among soft ones

**Measurement hints**
- frames.sharpness_map_grid contrast between subject and surroundings

**Not to be confused with**
- [`isolation`](#isolation): Isolation uses an even empty field; dof uses blur.

**Related:** realized_by [`shallow_depth_of_field`](#shallow_depth_of_field)

**Prompt phrase:** "Selective focus isolating the subject."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="texture"></a>
### texture

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `texture`

Contrast between flat areas and busy, detailed areas.

**Observable cues**
- Smooth zones next to highly textured zones

**Measurement hints**
- Large spatial variance of local edge density

**Not to be confused with**
- [`facture`](#facture): Facture shows how the image was made; texture contrasts surface qualities.

**Prompt phrase:** "Crisp crunchy texture against a smooth plain surface."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="facture"></a>
### facture

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `facture`

A visible cue to how the image was made or transformed contributes to its meaning (hand vs machine).

**Observable cues**
- Visible brush strokes, hand-drawn lines, glitch, visible construction

**Measurement hints**
- Reviewer must point to the visible cue; texture or equipment alone is insufficient

**Not to be confused with**
- [`texture`](#texture): Texture alone is not facture.
- [`genre`](#genre): A genre look is about conventions, not making-process traces.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="isolation"></a>
### isolation

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `isolation`

A single subject alone in an even, uniform field.

**Observable cues**
- One subject, uniform background, nothing competing

**Measurement hints**
- Background region has low edge density and low colour variance; one salient object

**Not to be confused with**
- [`dof`](#dof): dof isolates with blur; isolation uses an empty even field.
- [`negative_space`](#negative_space): negative_space is the measured empty area.

**Related:** realized_by [`negative_space`](#negative_space)

**Prompt phrase:** "A single subject isolated on a clean, even background."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="popout"></a>
### popout

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `popout`

One element is conspicuously different from a set of similar elements (a red dot among black dots).

**Observable cues**
- One odd element in a field of similar ones

**Measurement hints**
- Outlier in colour/shape among repeated elements

**Not to be confused with**
- [`patternbreak`](#patternbreak): Pattern break violates a rule; pop-out is a conspicuous feature.
- [`accent_color`](#accent_color): accent_color is the measured palette role.

**Related:** realized_by [`accent_color`](#accent_color)

**Prompt phrase:** "One bright red tomato among green leaves."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="scaledisparity"></a>
### scaledisparity

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `scaledisparity`

A marked difference in size between elements creates emphasis.

**Observable cues**
- One element much larger than the others

**Measurement hints**
- Area ratio between largest and next element > ~4

**Not to be confused with**
- [`hierarchy`](#hierarchy): Size hierarchy orders reading; scale disparity creates contrast.
- [`forcedperspective`](#forcedperspective): Forced perspective fakes relative scale with depth.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="caricature"></a>
### caricature

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `caricature`

A feature is exaggerated beyond the norm, and the eye compares it with the norm.

**Observable cues**
- Exaggerated proportion relative to an expected norm

**Measurement hints**
- Reviewer identifies the norm and the overshoot

**Not to be confused with**
- [`scaledisparity`](#scaledisparity): Scale disparity compares elements; caricature compares a feature to its norm.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="juxtaposition"></a>
### juxtaposition

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `juxtaposition`

Two different things placed side by side so they are compared.

**Observable cues**
- Two contrasting objects or states next to each other (before/after)

**Measurement hints**
- Two salient regions of similar weight with contrasting content

**Not to be confused with**
- [`contrast`](#contrast): narrative.function contrast is the story role; juxtaposition is the visual arrangement.

**Related:** can_realize [`contrast`](#contrast)

**Prompt phrase:** "Two contrasting plates side by side."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="patternbreak"></a>
### patternbreak

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `patternbreak`

A repeated rule is violated by one element.

**Observable cues**
- Regular repetition with one deviation

**Measurement hints**
- Periodic pattern with one outlier position or orientation

**Not to be confused with**
- [`popout`](#popout): Pop-out is a conspicuous feature; pattern break is a violated rule.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="proximity"></a>
### proximity

dimension `composition` | unit `frame` | claim `estimated` | **unverified** | Iris technique `proximity`

Elements that are close together are perceived as a group.

**Observable cues**
- Clusters separated by gaps

**Measurement hints**
- Spatial clustering of elements with clear inter-cluster gaps

**Not to be confused with**
- [`commonregion`](#commonregion): Common region groups by a shared container, not distance.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="similarity"></a>
### similarity

dimension `composition` | unit `frame` | claim `estimated` | **unverified** | Iris technique `similarity`

Elements that look alike are perceived as a group.

**Observable cues**
- Repeated colour/shape across the frame links elements

**Measurement hints**
- Feature similarity clusters independent of position

**Not to be confused with**
- [`proximity`](#proximity): Proximity groups by distance.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="commonregion"></a>
### commonregion

dimension `composition` | unit `frame` | claim `estimated` | **unverified** | Iris technique `commonregion`

Elements inside the same outline or container are perceived together.

**Observable cues**
- Items grouped inside a card, plate, box or frame

**Measurement hints**
- Elements enclosed by one contour

**Not to be confused with**
- [`framewithin`](#framewithin): Frame within frame directs attention; common region groups.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="continuity"></a>
### continuity

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `continuity`

Good continuation: the eye follows a smooth line or trajectory through elements.

**Observable cues**
- Elements aligned along a smooth curve or line

**Measurement hints**
- Collinear or smoothly curving alignment of element centroids

**Not to be confused with**
- [`leadinglines`](#leadinglines): Leading lines point to a target; good continuation is a smooth path through elements.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="symmetry"></a>
### symmetry

dimension `composition` | unit `frame` | claim `measured` | verified | Iris technique `symmetry`

Left and right halves mirror each other.

**Observable cues**
- Mirror balance around a vertical axis

**Measurement hints**
- High left-right mirrored SSIM of the keyframe

**Not to be confused with**
- [`centered_composition`](#centered_composition): Centred placement need not be symmetric.

**Prompt phrase:** "Perfectly symmetrical frontal composition."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="figureground"></a>
### figureground

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `figureground`

A large figure is clearly separated from the background.

**Observable cues**
- Large figure with clear boundary against a distinct ground

**Measurement hints**
- Strong luma/colour difference along the subject boundary; large subject area

**Not to be confused with**
- [`isolation`](#isolation): Isolation needs an empty field; figure-ground only needs separation.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="closure"></a>
### closure

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `closure`

The viewer completes a shape that has missing parts.

**Observable cues**
- Incomplete outline that still reads as a whole

**Measurement hints**
- Reviewer identifies the implied shape

**Not to be confused with**
- [`crop`](#crop): Crop hides part of a subject with the frame edge; closure is an implied shape.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="compounding"></a>
### compounding

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `compounding`

Distinct signs linked by a shared baseline combine into one meaning: association, not likeness.

**Observable cues**
- Separate signs aligned to form a phrase or composite meaning

**Measurement hints**
- Reviewer explains the association

**Not to be confused with**
- [`substitution`](#substitution): Substitution replaces one object with another by likeness.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="leadinglines"></a>
### leadinglines

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `leadinglines`

Lines in the image lead toward the point of interest.

**Observable cues**
- Converging lines (table edges, utensils, roads) pointing at the subject

**Measurement hints**
- Detected lines converge near the subject centroid

**Not to be confused with**
- [`continuity`](#continuity): Good continuation is a path through elements; leading lines point to a target.

**Prompt phrase:** "Leading lines guiding the eye to the plate."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="gaze"></a>
### gaze

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `gaze`

A depicted figure's gaze directs the viewer's attention.

**Observable cues**
- Person looking at the product or a text element

**Measurement hints**
- Head pose/eye direction vector intersects a salient object

**Not to be confused with**
- [`vector`](#vector): Vector uses body or gesture direction rather than eyes.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="vector"></a>
### vector

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `vector`

The direction of a body, pose or gesture points the viewer somewhere (body vector).

**Observable cues**
- Pointing hand, leaning body, arrow-like pose

**Measurement hints**
- Pose keypoints define a direction toward a target

**Not to be confused with**
- [`gaze`](#gaze): Gaze uses the eyes.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="hierarchy"></a>
### hierarchy

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `hierarchy`

Size or weight hierarchy orders what is read first, second, third.

**Observable cues**
- Clear ordering of element sizes or weights (headline > subline > label)

**Measurement hints**
- Monotonic size ranking among text/graphic elements (text.glyph_height_rel)

**Not to be confused with**
- [`scaledisparity`](#scaledisparity): Scale disparity creates contrast; hierarchy creates an order.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="readingpath"></a>
### readingpath

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `readingpath`

Elements are arranged along a reading route (Z, F, zigzag).

**Observable cues**
- Elements placed along a Z or F path

**Measurement hints**
- Ordered salient points follow a Z/F pattern

**Not to be confused with**
- [`hierarchy`](#hierarchy): Hierarchy orders by size; reading path orders by position.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="centralbias"></a>
### centralbias

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `centralbias`

Attention goes to a figure near the centre.

**Observable cues**
- Main figure near the frame centre

**Measurement hints**
- Subject centroid near (0.5, 0.5)

**Not to be confused with**
- [`centered_composition`](#centered_composition): centered_composition is the measured placement.

**Related:** realized_by [`centered_composition`](#centered_composition)

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="framewithin"></a>
### framewithin

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `framewithin`

A frame inside the frame (door, window, phone screen, plate rim) encloses the subject.

**Observable cues**
- Subject enclosed by an inner rectangle or border

**Measurement hints**
- Inner closed contour surrounding the subject

**Not to be confused with**
- [`commonregion`](#commonregion): Common region groups items; frame-within directs to the framed subject.

**Prompt phrase:** "The subject framed through a doorway."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="crop"></a>
### crop

dimension `composition` | unit `frame` | claim `measured` | verified | Iris technique `crop`

The frame edge hides part of the subject.

**Observable cues**
- Subject cut by the frame edge

**Measurement hints**
- Subject mask touches a frame border

**Not to be confused with**
- [`occlusion`](#occlusion): Occlusion: an object hides; crop: the frame hides.
- [`crop_animation`](#crop_animation): crop_animation is an editorial move, not this static technique.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="occlusion"></a>
### occlusion

dimension `composition` | unit `frame` | claim `estimated` | verified | Iris technique `occlusion`

An object hides part of another object.

**Observable cues**
- Foreground object partly covering the subject

**Measurement hints**
- Overlapping masks with depth ordering

**Not to be confused with**
- [`crop`](#crop): Crop is done by the frame edge.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="forcedperspective"></a>
### forcedperspective

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `forcedperspective`

Depth is used to fake relative scale.

**Observable cues**
- Near object appears to interact with a far object at implausible scale

**Measurement hints**
- Reviewer identifies the depth trick

**Not to be confused with**
- [`scaledisparity`](#scaledisparity): Scale disparity can be real sizes; forced perspective fakes it.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="temporalsynthesis"></a>
### temporalsynthesis

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `temporalsynthesis`

Several instants are visible in one field: accumulated time, not an arrow or a clock.

**Observable cues**
- Multiple exposures, motion trails, before and after in one frame

**Measurement hints**
- Repeated subject instances within one frame

**Not to be confused with**
- [`ghosting`](#ghosting): Ghosting is an unwanted double contour; temporal synthesis is deliberate.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="pareidolia"></a>
### pareidolia

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `pareidolia`

A face or figure is seen in something that is not one.

**Observable cues**
- Arrangement reads as a face

**Measurement hints**
- Face detector fires on a non-face object

**Not to be confused with**
- [`personification`](#personification): Personification deliberately gives human traits; pareidolia is perceived.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="personification"></a>
### personification

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `personification`

An object is given human traits (eyes, mouth, limbs, behaviour).

**Observable cues**
- Object with face or limbs, acting like a person

**Measurement hints**
- Reviewer identifies the human trait

**Not to be confused with**
- [`pareidolia`](#pareidolia): Pareidolia is incidental.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="displacement"></a>
### displacement

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `displacement`

An object appears in a place where it does not belong.

**Observable cues**
- Out-of-context object placement

**Measurement hints**
- Reviewer identifies the expected context

**Not to be confused with**
- [`contextual`](#contextual): Contextual gives the object a new role; displacement is the incongruity itself.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="substitution"></a>
### substitution

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `substitution`

One object takes the place of another by likeness.

**Observable cues**
- An object stands in for another of similar shape

**Measurement hints**
- Reviewer names the replaced object

**Not to be confused with**
- [`compounding`](#compounding): Compounding links distinct signs by association.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="contextual"></a>
### contextual

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `contextual`

The setting gives an object a new role (a pencil among clouds plays a mountain).

**Observable cues**
- Object reinterpreted by its surroundings

**Measurement hints**
- Reviewer names the borrowed role

**Not to be confused with**
- [`displacement`](#displacement): Displacement only needs incongruity.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="inscenetext"></a>
### inscenetext

dimension `composition` | unit `frame` | claim `estimated` | **unverified** | Iris technique `inscenetext`

Text that exists inside the scene (a label, a sign, a phone UI) rather than an overlay.

**Observable cues**
- Text on packaging, signage or a device screen in the scene

**Measurement hints**
- text.class in {label, ui, ambient} with scene-attached trajectory

**Not to be confused with**
- [`subject_attached`](#subject_attached): subject_attached is an overlay that tracks an object; in-scene text is physically there.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="genre"></a>
### genre

dimension `composition` | unit `frame` | claim `interpreted` | **unverified** | Iris technique `genre`

Conventions of a recognisable genre are used (infomercial, recipe video, noir, unboxing).

**Observable cues**
- Recognisable genre conventions in framing, type and pacing

**Measurement hints**
- Reviewer names the genre and its conventions

**Not to be confused with**
- [`genrequotation`](#genrequotation): Quotation deliberately cites a genre; genre simply follows its conventions.

**Verification note:** Iris technique ID verified from the public marks.js; the Iris definition is gated, so this meaning is inferred from the ID and icon only.

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="genrequotation"></a>
### genrequotation

dimension `composition` | unit `frame` | claim `interpreted` | verified | Iris technique `genrequotation`

A genre's conventions are quoted, often ironically, as a reference.

**Observable cues**
- Borrowed genre look used out of its context

**Measurement hints**
- Reviewer names the quoted genre

**Not to be confused with**
- [`genre`](#genre): Never attach visual quotation and genre quotation to the same borrowed reference.

**Verification note:** Iris technique ID verified; meaning supported by a literal hint in the public Iris code (see iris-taxonomia.md section 3).

**Sources**
- [Iris - A Taxonomy of Visuals (public site; technique IDs from marks.js, extracted in local iris-taxonomia.md)](https://visuals.modernartdirection.com/) (accessed 2026-10-31)

---

<a id="dim-montage-transition"></a>
## montage.transition

Temporal unit `sequence`, cardinality `single`.

How one shot passes to the next. Transitions are modelled as half-open intervals [start, end) that may overlap two shots; 1-3 frame events are kept as candidates. Temporal unit follows the shot/segment levels of film annotation ontologies such as AdA.

- Qualifier `color`: black, white, other (applies to fade). Colour reached by a fade or dip.
- Qualifier `direction`: left, right, up, down, radial (applies to wipe, whip_transition). Direction of a wipe or whip.

Measurement keys: `shots.boundaries`, `shots.transition_candidates`, `frames.diff_prev_ssim`, `frames.diff_prev_hist`, `frames.L_mean`, `motion.motion_blur_streak`, `shots.short_events`

<a id="hard_cut"></a>
### hard_cut

dimension `montage.transition` | unit `sequence` | claim `measured` | verified

An instantaneous change from one shot to the next with no intermediate frames.

**Aliases:** cut; hard cut; clean cut; straight cut

**Observable cues**
- Content changes completely between two consecutive frames

**Measurement hints**
- Single-frame spike in frames.diff_prev_hist and 1-SSIM with no ramp; shots.boundaries marks one frame

**Not to be confused with**
- [`jump_cut`](#jump_cut): A jump cut keeps the same framing and subject, skipping time.
- [`cross_dissolve`](#cross_dissolve): A dissolve ramps over several frames.

**Prompt phrase:** "Hard cut to the next shot."

**Bindings**
- effectcraft-0.17: exact - layer.timing
- ffmpeg: exact - concat
- higgsfield-cinema-3.5: approx - multi_shots=True, multi_shot_mode=custom
- higgsfield-cinema-v2: approx - multi_shots=True, multi_shot_mode=custom
- higgsfield-kling-3.0: approx - kling_o3_flf: multi_shots=True

**Dictionary:** HF-0194

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [AdA Filmontology (annotation levels, types, values)](https://projectada.github.io/ontology/) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="jump_cut"></a>
### jump_cut

dimension `montage.transition` | unit `sequence` | claim `measured` | **unverified**

A cut between two moments of the same shot or framing, producing a visible jump in time (typical of talking-head edits).

**Aliases:** jump cut

**Observable cues**
- Same background and framing, subject position jumps

**Measurement hints**
- Cut detected but background region pHash nearly identical across the boundary; subject mask displaced

**Not to be confused with**
- [`hard_cut`](#hard_cut): A hard cut changes the shot.
- [`punch_in`](#punch_in): A punch-in also changes scale at the cut; record both if present.

**Prompt phrase:** "Jump cut within the same framing."

**Bindings**
- ffmpeg: approx - trim,setpts

**Verification note:** Standard editing term; not found in the consulted Higgsfield guides.

**Sources**
- [AdA Filmontology (annotation levels, types, values)](https://projectada.github.io/ontology/) (accessed 2026-11-01)

---

<a id="match_cut"></a>
### match_cut

dimension `montage.transition` | unit `sequence` | claim `interpreted` | verified

A cut that links two shots through similar shape, position, movement or action.

**Aliases:** Match cut; match cut; graphic match

**Observable cues**
- Matching silhouette, position or motion direction across the cut

**Measurement hints**
- High shape/position similarity of salient masks across the boundary (IoU of subject masks) while content differs

**Not to be confused with**
- [`morph_transition`](#morph_transition): A morph interpolates frames between the shapes; a match cut is instantaneous.

**Prompt phrase:** "Match cut on the round shape of the plate."

**Dictionary:** HF-0195

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="cross_dissolve"></a>
### cross_dissolve

dimension `montage.transition` | unit `sequence` | claim `measured` | verified

Two shots blend over several frames, one fading out as the other fades in.

**Aliases:** dissolve; crossfade; mix

**Observable cues**
- Double exposure of both shots for several frames

**Measurement hints**
- Monotonic ramp of frames.diff_prev_hist over 4-30 frames; pixel values are a linear mix of both shots

**Not to be confused with**
- [`fade`](#fade): A fade passes through a solid colour.
- [`rack_focus`](#rack_focus): A rack focus keeps a single image.

**Prompt phrase:** "Slow cross dissolve between the shots."

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/opacity linear
- ffmpeg: exact - xfade

**Dictionary:** HF-0208

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)

---

<a id="fade"></a>
### fade

dimension `montage.transition` | unit `sequence` | claim `measured` | verified

The image fades to or from a solid colour (black by default; white is a 'dip to white' or flash).

**Aliases:** fade to black; fade in; fade out; dip to white; flash frame; flash transition

**Observable cues**
- Picture darkens or brightens to a flat colour, then the next shot appears

**Measurement hints**
- frames.L_mean ramps toward 0 (or 100) with near-zero variance at the extreme

**Not to be confused with**
- [`cross_dissolve`](#cross_dissolve): A dissolve never reaches a flat colour.
- [`flicker`](#flicker): Flicker is unintended brightness instability.

**Prompt phrase:** "Fade to black."

**Bindings**
- effectcraft-0.17: approx - layer.newSolid
- ffmpeg: exact - xfade
- ffmpeg: exact - xfade

**Dictionary:** HF-0208

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)

---

<a id="wipe"></a>
### wipe

dimension `montage.transition` | unit `sequence` | claim `measured` | verified

A boundary sweeps across the frame, replacing one shot with the next.

**Aliases:** linear wipe; radial wipe; iris wipe

**Observable cues**
- Moving edge (straight, radial or shaped) separating two shots

**Measurement hints**
- A coherent moving boundary between two content regions over several frames

**Not to be confused with**
- [`mask_transition`](#mask_transition): A mask transition uses an object in the scene as the wiping edge.

**Prompt phrase:** "Linear wipe to the next shot."

**Bindings**
- effectcraft-0.17: exact - add_effect ec.transition.linearwipe
- ffmpeg: exact - xfade

**Dictionary:** HF-0208

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)

---

<a id="whip_transition"></a>
### whip_transition

dimension `montage.transition` | unit `sequence` | claim `estimated` | verified

A cut hidden inside a whip pan or fast directional blur, so two shots seem connected by one camera swish.

**Aliases:** whip-pan cut; swish transition; whip

**Observable cues**
- Strong directional blur on both sides of the boundary

**Measurement hints**
- Cut detected inside a window with high motion.motion_blur_streak in a consistent direction

**Not to be confused with**
- [`whip_pan`](#whip_pan): whip_pan is the camera movement; whip_transition records that a cut is hidden inside it.

**Prompt phrase:** "Whip-pan transition into the next shot."

**Bindings**
- effectcraft-0.17: approx - add_effect ec.blur.directional
- ffmpeg: approx - xfade

**Dictionary:** HF-0068

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="mask_transition"></a>
### mask_transition

dimension `montage.transition` | unit `sequence` | claim `estimated` | verified

An object (a hand, a passing body, the product) covers the lens or a large area and the next shot is revealed behind it.

**Aliases:** Hand Transition; object wipe; occlusion transition; pass-by transition

**Observable cues**
- Foreground object fills the frame at the boundary, then the next shot emerges

**Measurement hints**
- Large occluding region with low texture at the boundary frames, then content change

**Not to be confused with**
- [`wipe`](#wipe): A wipe uses a graphic edge, not a scene object.
- [`hard_cut`](#hard_cut): A plain cut has no covering object.

**Prompt phrase:** "A hand sweeps across the lens, revealing the next shot."

**Bindings**
- effectcraft-0.17: approx - layer.setTrackMatte
- ffmpeg: approx - xfade
- higgsfield-camera-controls: also - preset 'Through Object In'
- higgsfield-camera-controls: also - preset 'Through Object Out'

**Dictionary:** HF-0395

**Sources**
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)

---

<a id="morph_transition"></a>
### morph_transition

dimension `montage.transition` | unit `sequence` | claim `estimated` | verified

Shapes deform continuously from the first shot into the second (typical of AI start/end frame generation).

**Aliases:** Morph Transition; morph; start/end frame transition; Melt Transition

**Observable cues**
- Intermediate frames show shapes melting or reshaping between two compositions

**Measurement hints**
- Continuous high optical flow with non-rigid deformation across frames; no single cut frame

**Not to be confused with**
- [`match_cut`](#match_cut): A match cut is instantaneous.
- [`motion_morphing`](#motion_morphing): Unintended morphing is a defect inside a shot.

**Prompt phrase:** "Morph seamlessly from the first frame into the last frame."

**Bindings**
- higgsfield-cinema-3.5: approx - media:start_image, media:end_image
- higgsfield-cinema-4.0: approx - media:start_image, media:end_image
- higgsfield-cinema-v2: approx - media:start_image, media:end_image
- higgsfield-kling-3.0: approx - media:start_image, media:end_image
- higgsfield-kling-4.0: approx - mode=image-to-video, media:start_image, media:end_image
- higgsfield-seedance-2.5: approx - media:start_image, media:end_image

**Dictionary:** HF-0395, HF-0264, HF-0265

**Sources**
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)

---

<a id="dim-montage-pacing"></a>
## montage.pacing

Temporal unit `video`, cardinality `single`.

Editing rhythm of a sequence or the whole video, measured from cut frequency and shot-length distribution.

Measurement keys: `shots.cuts_per_second`, `shots.duration_s`, `shots.duration_cv`, `shots.unique_images_phash`, `shots.reuse_count`

<a id="single_continuous_shot"></a>
### single_continuous_shot

dimension `montage.pacing` | unit `video` | claim `measured` | verified

The sequence plays without internal cuts.

**Aliases:** Single shot; one continuous shot; unbroken shot; one take; continuous take

**Observable cues**
- No cut for the whole sequence

**Measurement hints**
- shots.boundaries contains no cut inside the interval

**Not to be confused with**
- [`calm_pacing`](#calm_pacing): Calm pacing can include a few long shots.

**Prompt phrase:** "One continuous shot with no cuts."

**Bindings**
- higgsfield-cinema-3.5: approx - multi_shots=False
- higgsfield-cinema-4.0: exact - pacing_id=<Single shot>
- higgsfield-cinema-v2: approx - multi_shots=False
- higgsfield-kling-3.0: approx - kling_o3_flf: multi_shots=False

**Dictionary:** HF-0192

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 2.0 Prompting Guide](https://higgsfield.ai/blog/seedance-prompting-guide) (accessed 2026-11-01)

---

<a id="calm_pacing"></a>
### calm_pacing

dimension `montage.pacing` | unit `video` | claim `measured` | verified

Few cuts and long shots; the eye can settle.

**Aliases:** Calm; slow pacing

**Observable cues**
- Shots last several seconds

**Measurement hints**
- Mean shot duration > ~3 s (cuts_per_second < ~0.33)

**Not to be confused with**
- [`dynamic_pacing`](#dynamic_pacing): Dynamic pacing cuts every 1-2 s.

**Prompt phrase:** "Calm, unhurried pacing with long takes."

**Bindings**
- higgsfield-cinema-4.0: exact - pacing_id=<Calm>

**Dictionary:** HF-0197, HF-0356

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="dynamic_pacing"></a>
### dynamic_pacing

dimension `montage.pacing` | unit `video` | claim `measured` | verified

Regular, energetic cutting with shots around one to two seconds.

**Aliases:** Dynamic; fast pacing

**Observable cues**
- Frequent cuts with readable shots

**Measurement hints**
- Mean shot duration ~0.8-3 s with moderate shots.duration_cv

**Not to be confused with**
- [`chaotic_pacing`](#chaotic_pacing): Chaotic pacing is faster and irregular.

**Prompt phrase:** "Dynamic pacing with quick, rhythmic cuts."

**Bindings**
- higgsfield-cinema-4.0: exact - pacing_id=<Dynamic>

**Dictionary:** HF-0197, HF-0356

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="chaotic_pacing"></a>
### chaotic_pacing

dimension `montage.pacing` | unit `video` | claim `measured` | verified

Very fast, irregular cutting where shots are barely readable.

**Aliases:** Chaotic; rapid-fire

**Observable cues**
- Rapid-fire cuts, sub-second shots, irregular rhythm

**Measurement hints**
- Mean shot duration < ~0.8 s and high shots.duration_cv

**Not to be confused with**
- [`dynamic_pacing`](#dynamic_pacing): Dynamic stays regular and readable.

**Prompt phrase:** "Chaotic rapid-fire editing."

**Bindings**
- higgsfield-cinema-4.0: exact - pacing_id=<Chaotic>

**Dictionary:** HF-0356

**Sources**
- [Cinema Studio 4.0 Complete Guide](https://higgsfield.ai/blog/cinema-studio-4-0-complete-guide) (accessed 2026-11-01)

---

<a id="dim-montage-speed"></a>
## montage.speed

Temporal unit `shot`, cardinality `single`.

Playback speed of the action relative to apparent real time.

Measurement keys: `shots.playback_rate_estimate`, `motion.velocity_profile`, `shots.frame_repeat_runs`, `audio.onsets`

<a id="real_time"></a>
### real_time

dimension `montage.speed` | unit `shot` | claim `estimated` | verified

Action plays at its apparent natural speed.

**Aliases:** Real-time; real-time motion; normal speed

**Observable cues**
- Gravity, liquids and gestures look natural

**Measurement hints**
- Falling objects match ~9.8 m/s^2 when scale is known; no frame repeats or blends

**Not to be confused with**
- [`slow_motion`](#slow_motion): Slow motion makes liquids and falls look viscous and slow.

**Prompt phrase:** "Real-time motion."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0198

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="slow_motion"></a>
### slow_motion

dimension `montage.speed` | unit `shot` | claim `estimated` | verified

Action plays slower than real time.

**Aliases:** Slow motion; slowmo; 120fps played at 24fps

**Observable cues**
- Splashes and pours hang in the air; hair and cloth drift

**Measurement hints**
- Low velocity for physically fast events; interpolated or blended frames possible

**Not to be confused with**
- [`speed_ramp`](#speed_ramp): A speed ramp changes speed during the shot.

**Prompt phrase:** "Slow motion as the sauce splashes."

**Bindings**
- effectcraft-0.17: exact - layer.timeStretch
- ffmpeg: exact - setpts,minterpolate
- higgsfield-camera-controls: approx - preset 'Bullet Time'
- higgsfield-camera-controls: also - preset 'Glam'
- higgsfield-cinema-v2: approx - speedramp=slowmo
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0199

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="fast_motion"></a>
### fast_motion

dimension `montage.speed` | unit `shot` | claim `estimated` | **unverified**

Action plays faster than real time without being a timelapse.

**Aliases:** speed-up; speedup; fast forward

**Observable cues**
- Gestures look jerky or hurried

**Measurement hints**
- Velocity of human motion well above natural ranges

**Not to be confused with**
- [`timelapse`](#timelapse): Timelapse compresses minutes or hours.

**Prompt phrase:** "Sped-up fast motion."

**Bindings**
- effectcraft-0.17: exact - layer.timeStretch
- ffmpeg: exact - setpts
- higgsfield-cinema-v2: approx - speedramp=speedup
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** 'speedup' appears as a cinematic_studio_video_v2.speedramp enum value; no guide defines it.

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="speed_ramp"></a>
### speed_ramp

dimension `montage.speed` | unit `shot` | claim `estimated` | verified

Playback speed changes within the shot, e.g. real time to slow motion at an impact.

**Aliases:** Speed ramp; speedramp; time ramp

**Observable cues**
- Action accelerates or decelerates abruptly

**Measurement hints**
- Step or ramp in shots.playback_rate_estimate inside one shot

**Not to be confused with**
- [`slow_motion`](#slow_motion): Constant slow motion has no change.

**Prompt phrase:** "Speed ramp into slow motion at the moment of impact."

**Bindings**
- effectcraft-0.17: approx - layer.enableTimeRemap
- ffmpeg: approx - setpts
- higgsfield-cinema-v2: approx - speedramp=custom
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0200

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="timelapse"></a>
### timelapse

dimension `montage.speed` | unit `shot` | claim `estimated` | verified

Long time spans compressed into seconds (clouds, crowds, cooking); hyperlapse adds camera travel.

**Aliases:** Timelapse Landscape; Timelapse Human; Timelapse Glam; Hyperlapse

**Observable cues**
- Light or shadows sweep visibly; crowds blur

**Measurement hints**
- Very high apparent velocity of slow processes; discontinuous micro-motion

**Not to be confused with**
- [`fast_motion`](#fast_motion): Fast motion is a mild speed-up of normal action.

**Prompt phrase:** "Timelapse of the meal being prepared."

**Bindings**
- effectcraft-0.17: approx - layer.timeStretch
- ffmpeg: approx - setpts
- higgsfield-camera-controls: approx - preset 'Hyperlapse'
- higgsfield-camera-controls: approx - preset 'Timelapse Glam'
- higgsfield-camera-controls: approx - preset 'Timelapse Human'
- higgsfield-camera-controls: approx - preset 'Timelapse Landscape'
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0464, HF-0465, HF-0440

**Sources**
- [Motion preset: Timelapse Human](https://higgsfield.ai/motion/b4ba822f-9171-4547-997e-c86de335385e) (accessed 2026-11-01)
- [Motion preset: Timelapse Landscape](https://higgsfield.ai/motion/d45f0a80-62b8-4651-bd62-0373a09b8f11) (accessed 2026-11-01)
- [Motion preset: Hyperlapse](https://higgsfield.ai/motion/f0f07997-34fe-4bef-84c1-ee9d4da94a1a) (accessed 2026-11-01)

---

<a id="reverse_playback"></a>
### reverse_playback

dimension `montage.speed` | unit `shot` | claim `estimated` | **unverified**

The shot plays backwards.

**Aliases:** reverse; rewind

**Observable cues**
- Liquids flow up; crumbs reassemble

**Measurement hints**
- Physically implausible flow direction (motion against gravity) sustained

**Not to be confused with**
- [`fast_motion`](#fast_motion): Fast motion plays forward; rewind effects are reverse_playback plus fast_motion.

**Prompt phrase:** "The pour plays in reverse."

**Bindings**
- effectcraft-0.17: exact - layer.timeReverse
- ffmpeg: exact - reverse
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Standard editing term; no Higgsfield source.

---

<a id="dim-edit-transform"></a>
## edit.transform

Temporal unit `shot`, cardinality `multi`.

Editorial transforms applied after capture (layer 3 of the four motion layers): digital zoom, crop animation, added shake, freeze, composites.

- Qualifier `direction`: left, right, up, down, in, out (applies to crop_animation, digital_zoom). Direction of the animated crop or zoom.

Measurement keys: `motion.edit_transform_candidates`, `motion.global_affine`, `motion.parallax_ratio`, `frames.sharpness_laplacian_var`, `frames.noise_residual`, `shots.frame_repeat_runs`

<a id="digital_zoom"></a>
### digital_zoom

dimension `edit.transform` | unit `shot` | claim `estimated` | **unverified**

A captured frame is progressively scaled up in post (Ken Burns), with no parallax and softening detail.

**Aliases:** Ken Burns; scale-up; post zoom

**Observable cues**
- Uniform enlargement; grain and noise enlarge with the image

**Measurement hints**
- Uniform scale with motion.parallax_ratio = 0 and decreasing frames.sharpness_laplacian_var; noise grain size grows

**Not to be confused with**
- [`zoom_in`](#zoom_in): Optical zoom keeps grain size and sharpness constant.
- [`dolly_in`](#dolly_in): A dolly shows parallax.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/scale linear
- ffmpeg: exact - zoompan

**Verification note:** Iris editing extension; the guide's 'Dolly versus zoom' distinction motivates it.

**Sources**
- [Camera Controls — Public Catalog](https://higgsfield.ai/camera-controls) (accessed 2026-11-01)

---

<a id="punch_in"></a>
### punch_in

dimension `edit.transform` | unit `shot` | claim `measured` | **unverified**

An instant scale step at a cut or mid-shot (jump zoom), common in talking-head edits.

**Aliases:** jump zoom; punch-in; scale jump

**Observable cues**
- Sudden tighter framing of the same take with no transition frames

**Measurement hints**
- Single-frame jump in motion.global_affine scale (> ~1.1x) with identical content

**Not to be confused with**
- [`crash_zoom_in`](#crash_zoom_in): A crash zoom has intermediate frames and blur.
- [`jump_cut`](#jump_cut): A jump cut skips time without scale change.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/scale hold
- ffmpeg: exact - crop,scale

**Verification note:** Common editing term; no Higgsfield source.

---

<a id="crop_animation"></a>
### crop_animation

dimension `edit.transform` | unit `shot` | claim `estimated` | **unverified**

A crop window pans or scans across a larger frame in post.

**Aliases:** animated crop; pan and scan; reframe animation

**Observable cues**
- Lateral or vertical scan over a still or video with no perspective change

**Measurement hints**
- Pure translation in motion.global_affine with zero parallax and no motion-blur increase

**Not to be confused with**
- [`pan_left`](#pan_left): A real pan adds motion blur and subtle perspective change at edges.
- [`apparent_lateral_travel`](#apparent_lateral_travel): Use when the cause is uncertain.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/position linear
- ffmpeg: exact - crop,scale

**Verification note:** Iris editing extension required by the four-layer motion model.

**Sources**
- [Camera Controls — Public Catalog](https://higgsfield.ai/camera-controls) (accessed 2026-11-01)

---

<a id="added_shake"></a>
### added_shake

dimension `edit.transform` | unit `shot` | claim `estimated` | **unverified**

Camera shake added in post: noise-like or periodic displacement identical across depth layers.

**Aliases:** camera shake effect; wiggle; impact shake

**Observable cues**
- Jitter identical for foreground and background; edge scaling to hide borders

**Measurement hints**
- motion.flow_jitter with zero parallax and spectrum typical of noise generators; constant overscan scale

**Not to be confused with**
- [`handheld`](#handheld): Real handheld shake produces parallax and rolling-shutter cues.
- [`jitter`](#jitter): jitter (defect) is unintended instability.

**Bindings**
- effectcraft-0.17: approx - prop.setExpression
- ffmpeg: approx - crop,scale
- higgsfield-camera-controls: also - preset 'Wiggle'

**Verification note:** Iris editing extension; Higgsfield 'Wiggle' preset is a generated shake, bound in camera-controls.

**Dictionary:** HF-0467

**Sources**
- [Motion preset: Wiggle](https://higgsfield.ai/motion/cfbe9732-1b5a-4f59-9dbc-801f85f5c702) (accessed 2026-11-01)

---

<a id="freeze_frame"></a>
### freeze_frame

dimension `edit.transform` | unit `shot` | claim `measured` | verified

A single frame is held, stopping all motion, often with a graphic or sound accent.

**Aliases:** Freeze frame; freeze; final freeze; held frame

**Observable cues**
- Everything stops, including noise and subject

**Measurement hints**
- shots.frame_repeat_runs: identical pHash and zero frame difference for > ~6 frames

**Not to be confused with**
- [`static`](#static): A static shot keeps the subject and noise moving.

**Bindings**
- effectcraft-0.17: approx - layer.timeStretch
- ffmpeg: exact - tpad

**Dictionary:** HF-0201

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="split_screen"></a>
### split_screen

dimension `edit.transform` | unit `shot` | claim `measured` | **unverified**

Two or more video panels share the frame at once.

**Aliases:** split-screen; picture-in-picture; side by side

**Observable cues**
- Hard straight boundary between independently moving panels

**Measurement hints**
- Persistent straight edge with uncorrelated flow on each side

**Not to be confused with**
- [`framewithin`](#framewithin): A frame within frame is inside one scene.
- [`green_screen_composite`](#green_screen_composite): A composite blends a subject into a new background, not panels.

**Bindings**
- effectcraft-0.17: approx - layer.newShape
- ffmpeg: exact - vstack

**Verification note:** Common editing term; no Higgsfield source.

---

<a id="green_screen_composite"></a>
### green_screen_composite

dimension `edit.transform` | unit `shot` | claim `estimated` | **unverified**

A keyed subject (often a creator) is composited over a separate background (image, screenshot, video).

**Aliases:** green screen; chroma key; background replacement; Location swap

**Observable cues**
- Edge halo or spill around the person; background lighting does not match the subject

**Measurement hints**
- Matte-like boundary with constant edge width; subject light direction inconsistent with background

**Not to be confused with**
- [`split_screen`](#split_screen): Split screen uses separate panels.
- A composite often shows light-direction mismatch between subject and background; note it in the claim.

**Bindings**
- effectcraft-0.17: exact - add_effect ec.keying.keylight
- ffmpeg: exact - chromakey,overlay

**Verification note:** Common creator-video technique; Higgsfield documents location swap and background removal workflows.

**Dictionary:** HF-0243, HF-0326

**Sources**
- [Gemini Omni Flash VFX](https://higgsfield.ai/blog/Higgsfield-Omni-VFX) (accessed 2026-11-01)
- [VFX in 4K](https://higgsfield.ai/blog/vfx_4k) (accessed 2026-11-01)
- [Edit Photos with AI](https://higgsfield.ai/blog/edit-photos-with-ai-higgsfield) (accessed 2026-11-01)

---

<a id="dim-graphic-motion"></a>
## graphic.motion

Temporal unit `shot`, cardinality `multi`.

Timing and easing of graphic elements (captions, shapes, masks, UI overlays; layer 4 of the motion model). Easing families are fitted to element trajectories with a residual error; the source project's keyframes are never claimed. Exactly one easing family per tracked move.

- Mutually exclusive: linear_easing, ease_in, ease_out, ease_in_out, spring_motion

Measurement keys: `motion.graphic_tracks`, `motion.easing_fit`, `motion.overshoot_ratio`, `motion.settle_time_ms`, `motion.hold_duration_ms`, `motion.stagger_offsets_ms`, `text.animation_events`

<a id="linear_easing"></a>
### linear_easing

dimension `graphic.motion` | unit `shot` | claim `estimated` | verified

Progress changes at a constant rate from start to end.

**Aliases:** linear; IR-0002 Linear easing

**Observable cues**
- Element moves at constant speed and stops abruptly

**Measurement hints**
- Best fit is cubic-bezier(0,0,1,1) with the lowest residual; flat velocity profile

**Not to be confused with**
- [`ease_out`](#ease_out): Ease-out decelerates into the end.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/position linear

**Dictionary:** IR-0002, IR-0001

**Sources**
- [W3C CSS Easing Functions Level 1 (CRD 2023-02-13)](https://www.w3.org/TR/css-easing-1/) (accessed 2026-11-01)
- [Adobe: Speed between keyframes (cited as A02 in the local EffectCraft guide; not re-opened)](https://helpx.adobe.com/after-effects/desktop/animate-in-after-effects/speed-between-keyframes/speed.html) (accessed 2026-10-30)

---

<a id="ease_in"></a>
### ease_in

dimension `graphic.motion` | unit `shot` | claim `estimated` | verified

Progress starts slow and accelerates toward the end.

**Aliases:** ease-in; accelerate

**Observable cues**
- Element departs gently and leaves fast

**Measurement hints**
- Best fit near cubic-bezier(0.42,0,1,1); velocity peaks at the end

**Not to be confused with**
- [`ease_out`](#ease_out): Ease-out is the mirror: fast start, slow end.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/position easyEaseOut

**Dictionary:** IR-0003, IR-0006

**Sources**
- [W3C CSS Easing Functions Level 1 (CRD 2023-02-13)](https://www.w3.org/TR/css-easing-1/) (accessed 2026-11-01)

---

<a id="ease_out"></a>
### ease_out

dimension `graphic.motion` | unit `shot` | claim `estimated` | verified

Progress starts fast and decelerates into the final position; the usual choice for entrances.

**Aliases:** ease-out; decelerate

**Observable cues**
- Element arrives quickly and settles gently

**Measurement hints**
- Best fit near cubic-bezier(0,0,0.58,1); velocity peaks at the start

**Not to be confused with**
- [`ease_in`](#ease_in): Ease-in accelerates instead.
- [`spring_motion`](#spring_motion): A spring overshoots and oscillates.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/position easyEaseIn

**Verification note:** In After Effects/EffectCraft naming, the deceleration into a key is 'easyEaseIn' on that key: names are inverted relative to CSS.

**Dictionary:** IR-0004

**Sources**
- [W3C CSS Easing Functions Level 1 (CRD 2023-02-13)](https://www.w3.org/TR/css-easing-1/) (accessed 2026-11-01)
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="ease_in_out"></a>
### ease_in_out

dimension `graphic.motion` | unit `shot` | claim `estimated` | verified

Progress accelerates then decelerates: slow start, fast middle, slow end.

**Aliases:** ease-in-out; easy ease; easyEase

**Observable cues**
- Smooth departure and arrival

**Measurement hints**
- Best fit near cubic-bezier(0.42,0,0.58,1); symmetric bell-shaped velocity

**Not to be confused with**
- [`linear_easing`](#linear_easing): Linear has a flat velocity profile.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/position easyEase

**Dictionary:** IR-0005

**Sources**
- [W3C CSS Easing Functions Level 1 (CRD 2023-02-13)](https://www.w3.org/TR/css-easing-1/) (accessed 2026-11-01)

---

<a id="spring_motion"></a>
### spring_motion

dimension `graphic.motion` | unit `shot` | claim `estimated` | **unverified**

Spring-like response: the element overshoots its target and oscillates with decaying amplitude before resting.

**Aliases:** spring; bounce; elastic; Elastic animation

**Observable cues**
- Bouncy arrival with one or more oscillations

**Measurement hints**
- Damped-oscillation fit beats bezier fits on residual; >= 1 sign change of velocity near the end

**Not to be confused with**
- [`overshoot`](#overshoot): A single excursion past the target without oscillation is overshoot with ease-out.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/scale easyEase

**Verification note:** Spring is an Iris extension; CSS easing defines no spring function.

**Dictionary:** IR-0008, HF-0239

**Sources**
- [W3C CSS Easing Functions Level 1 (CRD 2023-02-13)](https://www.w3.org/TR/css-easing-1/) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="overshoot"></a>
### overshoot

dimension `graphic.motion` | unit `shot` | claim `measured` | verified

A temporary excursion beyond the final value before returning (e.g. scale 96% to 103% to 100%).

**Aliases:** overshoot

**Observable cues**
- Element grows or travels slightly past its rest state and comes back

**Measurement hints**
- motion.overshoot_ratio > ~2% of travel

**Not to be confused with**
- [`spring_motion`](#spring_motion): Spring oscillates several times; overshoot is one excursion.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/scale easyEase

**Dictionary:** IR-0009

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="settle"></a>
### settle

dimension `graphic.motion` | unit `shot` | claim `measured` | verified

The final phase in which an element comes to rest within a tolerance; measured as settle time.

**Aliases:** settle time; settling

**Observable cues**
- Small residual motion that dies out before the hold

**Measurement hints**
- motion.settle_time_ms: time to stay within ~1% of the final value

**Not to be confused with**
- [`hold`](#hold): Hold begins after settling.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/scale easyEaseIn

**Dictionary:** IR-0010

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="hold"></a>
### hold

dimension `graphic.motion` | unit `shot` | claim `measured` | verified

An interval during which an element stays substantially unchanged, giving reading time.

**Aliases:** hold duration; dwell; reading hold

**Observable cues**
- Text stays perfectly still after arriving

**Measurement hints**
- motion.hold_duration_ms between end of settle and start of exit

**Not to be confused with**
- [`freeze_frame`](#freeze_frame): A freeze holds the whole picture; hold refers to one element.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/position hold

**Dictionary:** IR-0011, IR-0039

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="stagger"></a>
### stagger

dimension `graphic.motion` | unit `shot` | claim `measured` | verified

A systematic time offset between related elements (lines, words, cards) that otherwise animate the same way.

**Aliases:** offset; cascade; sequential delay

**Observable cues**
- Lines or letters arrive one after another with equal spacing

**Measurement hints**
- Regular motion.stagger_offsets_ms between onsets of similar tracks

**Not to be confused with**
- [`word_reveal`](#word_reveal): word_reveal is a caption style; stagger is the timing principle.

**Bindings**
- effectcraft-0.17: approx - layer.timing

**Dictionary:** IR-0014

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="anticipation"></a>
### anticipation

dimension `graphic.motion` | unit `shot` | claim `measured` | verified

A small preparatory movement in the opposite direction before the main action.

**Aliases:** wind-up; anticipation

**Observable cues**
- Element dips back or shrinks slightly before moving forward or growing

**Measurement hints**
- Initial velocity sign opposite to main travel for a few frames

**Not to be confused with**
- [`overshoot`](#overshoot): Overshoot happens after the action; anticipation before.

**Bindings**
- effectcraft-0.17: approx - add_keyframe transform/position easyEase

**Dictionary:** IR-0012

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="follow_through"></a>
### follow_through

dimension `graphic.motion` | unit `shot` | claim `estimated` | verified

Secondary parts keep moving after the main element stops (trailing letters, a swinging tag).

**Aliases:** follow-through; overlapping action; drag

**Observable cues**
- Parts lag and finish after the main body

**Measurement hints**
- Child track settle time later than parent track settle time

**Not to be confused with**
- [`settle`](#settle): Settle is the main element's rest; follow-through is secondary parts.

**Bindings**
- effectcraft-0.17: approx - layer.setParent

**Dictionary:** IR-0013

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="dim-typography-family_class"></a>
## typography.family_class

Temporal unit `shot`, cardinality `single`.

Broad typeface class of a text track. Exact font identity is only a candidate (closest_family), never a fact.

Measurement keys: `text.font_candidates`, `text.tracks`

<a id="geometric_sans"></a>
### geometric_sans

dimension `typography.family_class` | unit `shot` | claim `estimated` | verified

Sans-serif built from simple geometric shapes: near-circular O, single-storey a (Futura, Montserrat, Poppins).

**Aliases:** geometric sans-serif

**Observable cues**
- Round O, uniform strokes, single-storey a

**Measurement hints**
- Glyph O aspect ~1.0; low stroke modulation

**Not to be confused with**
- [`neo_grotesque_sans`](#neo_grotesque_sans): Neo-grotesques have narrower O and horizontal terminals.

**Sources**
- [Wikipedia: Sans-serif (grotesque, neo-grotesque, geometric, humanist classification)](https://en.wikipedia.org/wiki/Sans-serif) (accessed 2026-11-01)

---

<a id="neo_grotesque_sans"></a>
### neo_grotesque_sans

dimension `typography.family_class` | unit `shot` | claim `estimated` | verified

Mid-century style sans with uniform capitals and horizontal/vertical terminals (Helvetica, Inter, SF Pro).

**Aliases:** neo-grotesque; grotesque; grotesk

**Observable cues**
- Closed apertures; horizontal terminals on c, e, s

**Measurement hints**
- Low modulation, terminal angle ~0 degrees

**Not to be confused with**
- [`humanist_sans`](#humanist_sans): Humanist sans has open apertures and calligraphic modulation.

**Sources**
- [Wikipedia: Sans-serif (grotesque, neo-grotesque, geometric, humanist classification)](https://en.wikipedia.org/wiki/Sans-serif) (accessed 2026-11-01)

---

<a id="humanist_sans"></a>
### humanist_sans

dimension `typography.family_class` | unit `shot` | claim `estimated` | verified

Sans-serif derived from calligraphic forms with open apertures and some modulation (Gill Sans, Open Sans).

**Aliases:** humanist sans-serif

**Observable cues**
- Open apertures, slight stroke contrast

**Measurement hints**
- Moderate stroke modulation, angled terminals

**Not to be confused with**
- [`neo_grotesque_sans`](#neo_grotesque_sans): Neo-grotesques are more uniform and closed.

**Sources**
- [Wikipedia: Sans-serif (grotesque, neo-grotesque, geometric, humanist classification)](https://en.wikipedia.org/wiki/Sans-serif) (accessed 2026-11-01)

---

<a id="rounded_sans"></a>
### rounded_sans

dimension `typography.family_class` | unit `shot` | claim `estimated` | **unverified**

Sans-serif with rounded stroke ends and corners, common in friendly app UI and social captions.

**Aliases:** rounded

**Observable cues**
- Rounded terminals and corners

**Measurement hints**
- Corner curvature high at stroke ends in OCR crops

**Not to be confused with**
- [`geometric_sans`](#geometric_sans): Geometric sans has sharp terminals.

**Verification note:** Not a formal classification group in the cited source; kept as a practical class.

---

<a id="condensed_display"></a>
### condensed_display

dimension `typography.family_class` | unit `shot` | claim `estimated` | **unverified**

Tall, narrow, heavy display faces used for punchy headlines (Bebas, Impact, Anton).

**Aliases:** condensed; display; impact font

**Observable cues**
- Very narrow, tall glyphs, usually all caps and heavy

**Measurement hints**
- Glyph width/height ratio < ~0.45

**Not to be confused with**
- [`neo_grotesque_sans`](#neo_grotesque_sans): Regular-width grotesques are wider.

**Verification note:** Practical class; no formal source consulted.

---

<a id="serif"></a>
### serif

dimension `typography.family_class` | unit `shot` | claim `estimated` | verified

Typefaces with serifs at stroke ends (editorial, premium feel).

**Aliases:** serif; slab serif

**Observable cues**
- Small strokes (serifs) at the ends of letters

**Measurement hints**
- Serif detection on high-resolution OCR crops

**Not to be confused with**
- [`script`](#script): Script letters connect like handwriting.

**Sources**
- [Wikipedia: Sans-serif (grotesque, neo-grotesque, geometric, humanist classification)](https://en.wikipedia.org/wiki/Sans-serif) (accessed 2026-11-01)

---

<a id="script"></a>
### script

dimension `typography.family_class` | unit `shot` | claim `estimated` | **unverified**

Handwritten or calligraphic letterforms, often connected.

**Aliases:** handwritten; brush script

**Observable cues**
- Joined, slanted, brush or pen letters

**Measurement hints**
- Connected glyph components; high slant

**Not to be confused with**
- [`serif`](#serif): Serifs are disconnected print forms.

**Verification note:** Practical type class; no formal classification source was consulted.

---

<a id="dim-typography-weight"></a>
## typography.weight

Temporal unit `shot`, cardinality `single`.

Relative stroke thickness of a text track, mapped to CSS font-weight bands.

Measurement keys: `text.stroke_width_rel`, `text.font_candidates`, `text.fill_stroke_shadow`

<a id="light_weight"></a>
### light_weight

dimension `typography.weight` | unit `shot` | claim `estimated` | verified

Thin strokes (CSS 100-300).

**Aliases:** thin; light; 300

**Observable cues**
- Hairline-like strokes

**Measurement hints**
- Stroke width / glyph height < ~0.08

**Not to be confused with**
- [`regular_weight`](#regular_weight): Regular is visibly thicker.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Dictionary:** IR-0019

**Sources**
- [W3C CSS Fonts Module Level 4 (WD 2026-10-22), font-weight mapping](https://www.w3.org/TR/css-fonts-4/) (accessed 2026-11-01)

---

<a id="regular_weight"></a>
### regular_weight

dimension `typography.weight` | unit `shot` | claim `estimated` | verified

Book or normal strokes (CSS 400-500).

**Aliases:** normal; regular; 400

**Observable cues**
- Normal reading weight

**Measurement hints**
- Stroke width / glyph height ~0.08-0.13

**Not to be confused with**
- [`bold_weight`](#bold_weight): Bold is heavy and dark.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Dictionary:** IR-0019

**Sources**
- [W3C CSS Fonts Module Level 4 (WD 2026-10-22), font-weight mapping](https://www.w3.org/TR/css-fonts-4/) (accessed 2026-11-01)

---

<a id="bold_weight"></a>
### bold_weight

dimension `typography.weight` | unit `shot` | claim `estimated` | verified

Heavy strokes (CSS 600-900, bold to black).

**Aliases:** bold; semibold; black; heavy; 700; 900

**Observable cues**
- Thick dark strokes

**Measurement hints**
- Stroke width / glyph height > ~0.13

**Not to be confused with**
- An outline stroke thickens the silhouette but not the glyph weight; measure inside the fill.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Dictionary:** IR-0019

**Sources**
- [W3C CSS Fonts Module Level 4 (WD 2026-10-22), font-weight mapping](https://www.w3.org/TR/css-fonts-4/) (accessed 2026-11-01)

---

<a id="dim-typography-case"></a>
## typography.case

Temporal unit `shot`, cardinality `single`.

Letter case pattern of a text track from OCR content.

Measurement keys: `text.case_pattern`, `text.tracks`

<a id="all_caps"></a>
### all_caps

dimension `typography.case` | unit `shot` | claim `measured` | verified

Every letter uppercase.

**Aliases:** uppercase; caps

**Observable cues**
- Only capitals

**Measurement hints**
- OCR letters 100% uppercase

**Not to be confused with**
- [`title_case`](#title_case): Title case capitalises first letters only.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Dictionary:** IR-0018

**Sources**
- [W3C CSS Fonts Module Level 4 (WD 2026-10-22), font-weight mapping](https://www.w3.org/TR/css-fonts-4/) (accessed 2026-11-01)

---

<a id="sentence_case"></a>
### sentence_case

dimension `typography.case` | unit `shot` | claim `measured` | **unverified**

Only the first word (and proper nouns) capitalised.

**Aliases:** sentence case

**Observable cues**
- Normal sentence capitalisation

**Measurement hints**
- Capital only at sentence starts

**Not to be confused with**
- [`title_case`](#title_case): Title case capitalises most words.

**Verification note:** Common typographic convention; no external source was consulted.

**Dictionary:** IR-0018

---

<a id="title_case"></a>
### title_case

dimension `typography.case` | unit `shot` | claim `measured` | **unverified**

Most words start with a capital letter.

**Aliases:** Title Case

**Observable cues**
- Each Word Capitalised

**Measurement hints**
- Share of capitalised word-initials > ~0.7

**Not to be confused with**
- [`all_caps`](#all_caps): All caps capitalises every letter.

**Verification note:** Common typographic convention; no external source was consulted.

**Dictionary:** IR-0018

---

<a id="lowercase"></a>
### lowercase

dimension `typography.case` | unit `shot` | claim `measured` | **unverified**

Every letter lowercase, including sentence starts.

**Aliases:** all lowercase

**Observable cues**
- no capitals at all

**Measurement hints**
- OCR letters 100% lowercase

**Not to be confused with**
- [`sentence_case`](#sentence_case): Sentence case capitalises the first word.

**Verification note:** Common typographic convention; no external source was consulted.

**Dictionary:** IR-0018

---

<a id="dim-typography-entrance"></a>
## typography.entrance

Temporal unit `shot`, cardinality `single`.

How a text element enters (or, with qualifier phase=exit, leaves). Easing of the move is recorded separately in graphic.motion.

- Qualifier `phase`: entrance, exit. Whether the term describes the entrance or the exit.
- Qualifier `direction`: left, right, up, down (applies to slide_in). Origin direction of a slide.

Measurement keys: `text.tracks`, `text.class`, `text.glyph_height_rel`, `text.position_norm`, `text.font_candidates`, `text.stroke_width_rel`, `text.case_pattern`, `text.animation_events`, `text.local_contrast`, `motion.graphic_tracks`

<a id="cut_in"></a>
### cut_in

dimension `typography.entrance` | unit `shot` | claim `measured` | **unverified**

Text appears fully formed in one frame.

**Aliases:** pop on; hard in; cut out

**Observable cues**
- Text present in frame N, absent in frame N-1

**Measurement hints**
- Single-frame onset in text.tracks with full opacity

**Not to be confused with**
- [`fade_in`](#fade_in): A fade ramps opacity over frames.

**Bindings**
- effectcraft-0.17: exact - layer.timing
- ffmpeg: exact - drawtext

**Verification note:** Iris extension; no Higgsfield source.

---

<a id="fade_in"></a>
### fade_in

dimension `typography.entrance` | unit `shot` | claim `measured` | verified

Text appears or disappears through an opacity ramp.

**Aliases:** fade-in; fade-out; Fade-in / fade-out

**Observable cues**
- Gradual opacity change

**Measurement hints**
- text.local_contrast rising monotonically over several frames at a fixed position

**Not to be confused with**
- [`blur_in`](#blur_in): Blur-in sharpens from blur.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/opacity easyEase
- ffmpeg: exact - drawtext

**Dictionary:** IR-0031

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="slide_in"></a>
### slide_in

dimension `typography.entrance` | unit `shot` | claim `measured` | verified

Text travels into its resting position from outside it.

**Aliases:** slide-in; Slide-in; slide up

**Observable cues**
- Text moves along a path before resting

**Measurement hints**
- Position change in text.tracks trajectory before the hold

**Not to be confused with**
- [`mask_reveal`](#mask_reveal): A mask reveal shows text through a window; text may slide behind it.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/position easyEaseIn

**Dictionary:** IR-0030, IR-0032

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="scale_in"></a>
### scale_in

dimension `typography.entrance` | unit `shot` | claim `measured` | verified

Text grows (or shrinks) into its resting size, often with overshoot (pop).

**Aliases:** scale-in; Scale-in; pop; scale pop

**Observable cues**
- Text scales up from small

**Measurement hints**
- Increasing glyph height in text.glyph_height_rel before the hold

**Not to be confused with**
- [`word_highlight`](#word_highlight): Highlight changes emphasis of a word already on screen.

**Bindings**
- effectcraft-0.17: exact - add_keyframe transform/scale easyEaseIn

**Dictionary:** IR-0029

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="blur_in"></a>
### blur_in

dimension `typography.entrance` | unit `shot` | claim `measured` | **unverified**

Text resolves from a blurred state into sharp focus.

**Aliases:** blur-in; focus in

**Observable cues**
- Text sharpens over frames

**Measurement hints**
- Rising sharpness inside the text polygon while position is constant

**Not to be confused with**
- [`fade_in`](#fade_in): A fade changes opacity, not sharpness.

**Bindings**
- effectcraft-0.17: approx - layer.addTextAnimator

**Verification note:** Common text animator; Iris extension.

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="dim-typography-emphasis"></a>
## typography.emphasis

Temporal unit `shot`, cardinality `multi`.

Within-text emphasis and progressive reveal styles, especially for captions.

Measurement keys: `text.tracks`, `text.class`, `text.glyph_height_rel`, `text.position_norm`, `text.font_candidates`, `text.stroke_width_rel`, `text.case_pattern`, `text.animation_events`, `text.local_contrast`, `audio.transcript_words`, `audio.caption_voice_offset_ms`

<a id="word_highlight"></a>
### word_highlight

dimension `typography.emphasis` | unit `shot` | claim `measured` | verified

One word (or the currently spoken word) changes colour, box, weight or scale to stand out.

**Aliases:** karaoke highlight; active word; keyword emphasis

**Observable cues**
- The active word changes fill or gains a background box while the rest stays

**Measurement hints**
- Per-word colour/scale change events aligned to audio.transcript_words

**Not to be confused with**
- [`word_reveal`](#word_reveal): Word reveal adds words; highlight emphasises words already shown.

**Bindings**
- effectcraft-0.17: exact - layer.setText
- ffmpeg: approx - subtitles

**Dictionary:** IR-0024

**Sources**
- [W3C WAI: Captions/Subtitles](https://www.w3.org/WAI/media/av/captions/) (accessed 2026-11-01)

---

<a id="word_reveal"></a>
### word_reveal

dimension `typography.emphasis` | unit `shot` | claim `measured` | verified

Words appear one after another within a line or cue.

**Aliases:** word-by-word reveal

**Observable cues**
- Line builds up word by word

**Measurement hints**
- Word-level onsets in text.animation_events increasing within one cue

**Not to be confused with**
- [`typewriter`](#typewriter): Typewriter reveals character by character.

**Bindings**
- effectcraft-0.17: approx - layer.addTextAnimator

**Dictionary:** IR-0025

**Sources**
- [Adobe: Animating text (cited as A05 in the local EffectCraft guide; not re-opened)](https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html) (accessed 2026-10-30)

---

<a id="typewriter"></a>
### typewriter

dimension `typography.emphasis` | unit `shot` | claim `measured` | verified

Characters appear one at a time, like typing.

**Aliases:** typewriter reveal; type-on

**Observable cues**
- Text grows letter by letter, sometimes with a cursor

**Measurement hints**
- Character-level onsets at near-constant intervals

**Not to be confused with**
- [`word_reveal`](#word_reveal): Word reveal adds whole words.

**Bindings**
- effectcraft-0.17: approx - layer.addTextAnimator

**Dictionary:** IR-0026

**Sources**
- [Adobe: Animating text (cited as A05 in the local EffectCraft guide; not re-opened)](https://helpx.adobe.com/after-effects/desktop/animating-text/text-animation/animating-text.html) (accessed 2026-10-30)

---

<a id="line_reveal"></a>
### line_reveal

dimension `typography.emphasis` | unit `shot` | claim `measured` | verified

Complete lines appear one after another.

**Aliases:** line-by-line

**Observable cues**
- Line 1 then line 2

**Measurement hints**
- Line-level onsets staggered within one text block

**Not to be confused with**
- [`word_reveal`](#word_reveal): Word reveal operates within a line.

**Bindings**
- effectcraft-0.17: approx - layer.newText

**Dictionary:** IR-0027

**Sources**
- [Adobe: Create fluid text animations (cited as A01 in the local EffectCraft guide; not re-opened)](https://www.adobe.com/learn/after-effects/web/create-fluid-text-animations) (accessed 2026-10-30)

---

<a id="mask_reveal"></a>
### mask_reveal

dimension `typography.emphasis` | unit `shot` | claim `estimated` | verified

Text is exposed through an animated clipping window or track matte.

**Aliases:** masked reveal; matte reveal; Mask reveal

**Observable cues**
- Text emerges from behind an invisible edge

**Measurement hints**
- Text polygon partially visible with a straight clipping edge that moves while glyphs keep scale

**Not to be confused with**
- [`slide_in`](#slide_in): A plain slide shows the text travelling across open space.

**Bindings**
- effectcraft-0.17: exact - layer.setTrackMatte

**Dictionary:** IR-0028

**Sources**
- [Adobe: Track mattes and traveling mattes (cited as A06 in the local EffectCraft guide; not re-opened)](https://helpx.adobe.com/after-effects/desktop/work-with-transparency-and-compositing/work-with-track-mattes-and-traveling-mattes/track-mattes-and-traveling-mattes.html) (accessed 2026-10-30)

---

<a id="dim-typography-placement"></a>
## typography.placement

Temporal unit `shot`, cardinality `single`.

Vertical band where a text element rests in the 9:16 frame (normalised y of its centre), relative to platform safe areas.

- Qualifier `alignment`: left, center, right. Horizontal text alignment.

Measurement keys: `text.position_norm`, `text.tracks`, `frames.luma_band_safe_area`, `frames.luma_band_top`

<a id="upper_third"></a>
### upper_third

dimension `typography.placement` | unit `shot` | claim `measured` | **unverified**

Text rests in the top third of the frame.

**Aliases:** top text; header band

**Observable cues**
- Text above y=0.33

**Measurement hints**
- Text centre y < 0.33

**Not to be confused with**
- [`middle_band`](#middle_band): Middle band sits around the centre.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Verification note:** Iris layout band for 9:16 frames; a working convention, not a sourced standard.

**Dictionary:** IR-0023

---

<a id="middle_band"></a>
### middle_band

dimension `typography.placement` | unit `shot` | claim `measured` | **unverified**

Text rests around the vertical centre of the frame.

**Aliases:** center text; centre band

**Observable cues**
- Text across the middle

**Measurement hints**
- Text centre y 0.33-0.66

**Not to be confused with**
- [`lower_third`](#lower_third): Lower third sits near the bottom.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Verification note:** Iris layout band for 9:16 frames; a working convention, not a sourced standard.

---

<a id="lower_third"></a>
### lower_third

dimension `typography.placement` | unit `shot` | claim `measured` | **unverified**

Text rests in the bottom third (typical caption or name band), above platform UI.

**Aliases:** lower third; caption band

**Observable cues**
- Text below y=0.66

**Measurement hints**
- Text centre y > 0.66

**Not to be confused with**
- [`upper_third`](#upper_third): Upper third sits near the top.

**Bindings**
- effectcraft-0.17: exact - layer.newText

**Verification note:** Broadcast term used here as an Iris layout band for 9:16 frames; no source was consulted in this pass.

---

<a id="subject_attached"></a>
### subject_attached

dimension `typography.placement` | unit `shot` | claim `measured` | **unverified**

Text follows an object or person in the scene (tracked label or callout).

**Aliases:** tracked text; callout

**Observable cues**
- Label moves with the subject

**Measurement hints**
- text.tracks trajectory correlated with motion.subject_track

**Not to be confused with**
- [`inscenetext`](#inscenetext): In-scene text is physically part of the scene.

**Verification note:** Iris layout label; no external source.

---

<a id="dim-caption-cadence"></a>
## caption.cadence

Temporal unit `sequence`, cardinality `single`.

Chunking of speech-aligned captions: how many words a cue carries and how long it stays.

Measurement keys: `text.words_per_cue`, `text.cue_duration_s`, `text.chars_per_second`, `audio.caption_voice_offset_ms`, `audio.transcript_words`, `audio.words_per_minute`, `audio.pauses`

<a id="single_word_cues"></a>
### single_word_cues

dimension `caption.cadence` | unit `sequence` | claim `measured` | verified

Each caption cue shows one word.

**Aliases:** one word at a time

**Observable cues**
- Captions change with every word

**Measurement hints**
- Median text.words_per_cue = 1

**Not to be confused with**
- [`word_reveal`](#word_reveal): Word reveal keeps previous words on screen.

**Dictionary:** IR-0037

**Sources**
- [W3C WAI: Captions/Subtitles](https://www.w3.org/WAI/media/av/captions/) (accessed 2026-11-01)

---

<a id="phrase_cues"></a>
### phrase_cues

dimension `caption.cadence` | unit `sequence` | claim `measured` | verified

Each cue shows a short phrase of about two to five words.

**Aliases:** chunked captions

**Observable cues**
- Short chunks

**Measurement hints**
- Median text.words_per_cue 2-5

**Not to be confused with**
- [`sentence_cues`](#sentence_cues): Sentence cues carry whole sentences or two lines.

**Bindings**
- effectcraft-0.17: approx - layer.newText
- ffmpeg: exact - subtitles

**Dictionary:** IR-0037

**Sources**
- [W3C WAI: Captions/Subtitles](https://www.w3.org/WAI/media/av/captions/) (accessed 2026-11-01)

---

<a id="sentence_cues"></a>
### sentence_cues

dimension `caption.cadence` | unit `sequence` | claim `measured` | verified

Each cue shows a full sentence or a two-line block.

**Aliases:** full-sentence captions; subtitle blocks

**Observable cues**
- Long cues, often two lines

**Measurement hints**
- Median text.words_per_cue > 5

**Not to be confused with**
- [`phrase_cues`](#phrase_cues): Phrase cues are shorter.

**Dictionary:** IR-0037, HF-0283

**Sources**
- [W3C WAI: Captions/Subtitles](https://www.w3.org/WAI/media/av/captions/) (accessed 2026-11-01)
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="dim-sound-role"></a>
## sound.role

Temporal unit `video`, cardinality `multi`.

Which sound layers are present in a segment.

Measurement keys: `audio.speech_music_segments`, `audio.silence_segments`, `audio.onsets`, `audio.lufs_integrated`, `audio.transcript_words`, `audio.lra`, `audio.true_peak`, `audio.words_per_minute`, `audio.pauses`

<a id="voiceover"></a>
### voiceover

dimension `sound.role` | unit `video` | claim `estimated` | verified

Speech from an off-screen narrator, not lip-synced to anyone visible.

**Aliases:** VO; narration; Voiceover / narration

**Observable cues**
- Speech with no visible speaking mouth

**Measurement hints**
- Speech segments without matching mouth motion

**Not to be confused with**
- [`dialogue`](#dialogue): Dialogue is spoken on camera.

**Dictionary:** HF-0291

**Sources**
- [Higgsfield Audio](https://higgsfield.ai/blog/higgsfield-audio) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="dialogue"></a>
### dialogue

dimension `sound.role` | unit `video` | claim `estimated` | verified

On-camera speech, lip-synced to a visible speaker (talking head included).

**Aliases:** Dialogue; talking head; on-camera speech

**Observable cues**
- Visible mouth movement matches speech

**Measurement hints**
- Speech segments correlated with mouth motion

**Not to be confused with**
- [`voiceover`](#voiceover): Voiceover has no visible speaker.

**Dictionary:** HF-0290, HF-0297

**Sources**
- [Higgsfield Audio](https://higgsfield.ai/blog/higgsfield-audio) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Sports Product Video Ads](https://higgsfield.ai/blog/sports-product-video-ads-ai-2026) (accessed 2026-11-01)

---

<a id="score"></a>
### score

dimension `sound.role` | unit `video` | claim `estimated` | verified

Music accompanying the images (licensed track, trending audio or composed score).

**Aliases:** music; music bed; Score

**Observable cues**
- Musical content under the picture

**Measurement hints**
- Music segments in audio.speech_music_segments

**Not to be confused with**
- [`ambience`](#ambience): Ambience is non-musical environment sound.

**Dictionary:** HF-0296

**Sources**
- [Higgsfield Audio](https://higgsfield.ai/blog/higgsfield-audio) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="sound_effects"></a>
### sound_effects

dimension `sound.role` | unit `video` | claim `estimated` | verified

Discrete sounds tied to events (whoosh, pop, sizzle, click), including close foley.

**Aliases:** SFX; foley; whoosh; ASMR sounds

**Observable cues**
- Short sounds synced to visual events

**Measurement hints**
- Transient onsets aligned with visual events (cuts, impacts, text pops)

**Not to be confused with**
- [`score`](#score): Score is continuous music.

**Dictionary:** HF-0295, HF-0392

**Sources**
- [Higgsfield Audio](https://higgsfield.ai/blog/higgsfield-audio) (accessed 2026-11-01)
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [VFX in 4K](https://higgsfield.ai/blog/vfx_4k) (accessed 2026-11-01)
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)

---

<a id="ambience"></a>
### ambience

dimension `sound.role` | unit `video` | claim `estimated` | verified

Sustained environmental sound or room tone.

**Aliases:** ambient sound; room tone; diegetic background

**Observable cues**
- Background hum, street, kitchen

**Measurement hints**
- Low-level non-speech non-music bed between speech segments

**Not to be confused with**
- [`silence`](#silence): Silence has no measurable bed.

**Dictionary:** HF-0293, HF-0294, HF-0292

**Sources**
- [Higgsfield Audio](https://higgsfield.ai/blog/higgsfield-audio) (accessed 2026-11-01)
- [Gemini Omni Flash VFX](https://higgsfield.ai/blog/Higgsfield-Omni-VFX) (accessed 2026-11-01)

---

<a id="silence"></a>
### silence

dimension `sound.role` | unit `video` | claim `measured` | **unverified**

No audible sound (or a silent video).

**Aliases:** silent; no audio; sound off

**Observable cues**
- No audio track or digital silence

**Measurement hints**
- audio.silence_segments covering the interval; LUFS below about -60

**Not to be confused with**
- [`ambience`](#ambience): Quiet ambience is still sound.

**Bindings**
- higgsfield-cinema-3.5: approx - generate_audio=False
- higgsfield-cinema-4.0: approx - generate_audio=False
- higgsfield-cinema-v2: exact - sound=off
- higgsfield-kling-3.0: exact - sound=off
- higgsfield-seedance-2.5: exact - generate_audio=False

**Verification note:** Measurement state; no Higgsfield term.

**Sources**
- [Cinema Studio 4.0 · API playground](https://open.higgsfield.ai/models/higgsfield/cinema-studio/4.0/playground) (accessed 2026-11-01)

---

<a id="dim-sound-music_relation"></a>
## sound.music_relation

Temporal unit `sequence`, cardinality `multi`.

How picture events relate to the music.

Measurement keys: `audio.beat_grid`, `audio.onsets`, `audio.cut_onset_alignment`, `shots.boundaries`, `text.animation_events`, `audio.music_level_under_speech`

<a id="cut_on_beat"></a>
### cut_on_beat

dimension `sound.music_relation` | unit `sequence` | claim `measured` | verified

Cuts land on musical beats.

**Aliases:** Cut on the beat; beat cut; beat-synced edit

**Observable cues**
- Picture changes on the beat

**Measurement hints**
- audio.cut_onset_alignment: share of cuts within 40 ms of a beat/onset well above chance

**Not to be confused with**
- [`motion_on_beat`](#motion_on_beat): Motion-on-beat aligns accents without cuts; unsynced music shows chance-level alignment.

**Dictionary:** HF-0203

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="motion_on_beat"></a>
### motion_on_beat

dimension `sound.music_relation` | unit `sequence` | claim `measured` | **unverified**

Graphic or subject motion accents (text pops, impacts, zooms) land on beats, without needing a cut.

**Aliases:** hit points; accent on beat

**Observable cues**
- Text pops or impacts hit the beat

**Measurement hints**
- Onsets of text.animation_events or flow spikes within 40 ms of beats

**Not to be confused with**
- [`cut_on_beat`](#cut_on_beat): Cut on beat concerns cuts.

**Verification note:** The cited guide names cutting on the beat; motion accents landing on the beat is an Iris extension of that idea.

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="beat_drop_sync"></a>
### beat_drop_sync

dimension `sound.music_relation` | unit `sequence` | claim `estimated` | verified

A key visual moment (reveal, cut to hero shot) is placed on the music drop or downbeat after a build.

**Aliases:** drop sync; beat drop

**Observable cues**
- Big visual change exactly at the drop

**Measurement hints**
- Largest visual change of the sequence within 80 ms of the strongest onset after a build

**Not to be confused with**
- [`cut_on_beat`](#cut_on_beat): Regular beat cuts are not tied to one drop.

**Sources**
- [Higgsfield blog: Seedance 2.5 Prompting Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="ducking"></a>
### ducking

dimension `sound.music_relation` | unit `sequence` | claim `measured` | **unverified**

Music level dips under speech so the voice stays intelligible.

**Aliases:** sidechain ducking; music under voice

**Observable cues**
- Music gets quieter when someone speaks

**Measurement hints**
- audio.music_level_under_speech lower by > ~6 dB during speech segments

**Not to be confused with**
- [`score`](#score): Score names presence only.

**Bindings**
- ffmpeg: exact - sidechaincompress

**Verification note:** Standard audio-mixing term; no source was consulted in this pass.

---

<a id="dim-narrative-function"></a>
## narrative.function

Temporal unit `shot`, cardinality `multi`.

Story role of a shot or segment. Always interpreted: needs a supporting sequence and a reviewer reason; never a measured fact. Neutral description only; no marketing rule is implied.

Measurement keys: `sheets.keyframes`, `sheets.timeline_sheet`, `audio.transcript_words`, `text.tracks`, `review.reviewer_note`

<a id="hook"></a>
### hook

dimension `narrative.function` | unit `shot` | claim `interpreted` | verified

The opening beat designed to capture attention in the first seconds.

**Aliases:** Hook; opener

**Observable cues**
- First 1-3 s with a striking visual, question or text

**Measurement hints**
- Position in first ~3 s; high visual change or bold text

**Not to be confused with**
- [`demonstration`](#demonstration): A demonstration shows use over time after attention is won.

**Dictionary:** HF-0272

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)
- [Sports Product Video Ads](https://higgsfield.ai/blog/sports-product-video-ads-ai-2026) (accessed 2026-11-01)

---

<a id="demonstration"></a>
### demonstration

dimension `narrative.function` | unit `shot` | claim `interpreted` | verified

Shows the subject or product in use (step, feature, recipe action, app screen).

**Aliases:** demo; how-to; usage

**Observable cues**
- Hands using the product; UI interaction

**Measurement hints**
- Sustained hand_interaction or screen_recording segments

**Not to be confused with**
- [`reveal`](#reveal): A reveal is a single moment of becoming visible.

**Dictionary:** HF-0276

**Sources**
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)
- [AI Product Photos](https://higgsfield.ai/blog/how-to-make-ai-product-photos-without-a-studio) (accessed 2026-11-01)

---

<a id="contrast"></a>
### contrast

dimension `narrative.function` | unit `shot` | claim `interpreted` | **unverified**

A before/after or this-versus-that comparison.

**Aliases:** before/after; comparison

**Observable cues**
- Two states shown in succession or side by side

**Measurement hints**
- Paired segments with opposing content

**Not to be confused with**
- [`juxtaposition`](#juxtaposition): Juxtaposition is the visual arrangement; contrast is the story role.

**Verification note:** Iris narrative-function label; no external source.

---

<a id="reveal"></a>
### reveal

dimension `narrative.function` | unit `shot` | claim `interpreted` | verified

The moment a subject, product or result becomes visible or recognisable, often the payoff.

**Aliases:** Product reveal; payoff; hero shot; packshot

**Observable cues**
- Uncovering, pull-back or cut to hero shot

**Measurement hints**
- Salient subject appears after being hidden or small

**Not to be confused with**
- [`demonstration`](#demonstration): Demonstration shows use over time.

**Bindings**
- higgsfield-camera-controls: also - preset 'BTS'

**Dictionary:** HF-0271, HF-0267, HF-0268

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)
- [Cinematic Headphones · Ultra-Realistic Ads](https://higgsfield.ai/blog/cinematic_headphones) (accessed 2026-11-01)

---

<a id="cta"></a>
### cta

dimension `narrative.function` | unit `shot` | claim `interpreted` | verified

A call to take a specific action (download, follow, try).

**Aliases:** CTA; call to action

**Observable cues**
- Imperative text or speech near the end

**Measurement hints**
- Imperative verbs in text.tracks or transcript near the end

**Not to be confused with**
- [`reveal`](#reveal): A reveal shows; a CTA asks.

**Dictionary:** HF-0273

**Sources**
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)
- [Sports Product Video Ads](https://higgsfield.ai/blog/sports-product-video-ads-ai-2026) (accessed 2026-11-01)

---

<a id="transition_beat"></a>
### transition_beat

dimension `narrative.function` | unit `shot` | claim `interpreted` | verified

A short bridging beat that moves between ideas or locations without new information.

**Aliases:** bridge; visual beat

**Observable cues**
- Brief connective shot or effect

**Measurement hints**
- Short shot (< ~1 s) between two content segments, often with a transition effect

**Not to be confused with**
- [`hook`](#hook): A hook opens; a transition beat connects.

**Dictionary:** HF-0190

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="claim"></a>
### claim

dimension `narrative.function` | unit `shot` | claim `interpreted` | **unverified**

A beat that states the central assertion or promise of the piece.

**Observable cues**
- Declarative sentence that the rest of the video supports

**Measurement hints**
- Text cue or transcript sentence with no action verb on screen

**Not to be confused with**
- [`hook`](#hook): The hook captures attention; the claim states the thesis.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

---

<a id="setup"></a>
### setup

dimension `narrative.function` | unit `shot` | claim `interpreted` | **unverified**

A beat that establishes context, place, time or problem before the demonstration.

**Observable cues**
- Establishing shot, date card or problem statement

**Measurement hints**
- Often a wide shot or a text-only card

**Not to be confused with**
- [`demonstration`](#demonstration): Setup explains; demonstration shows.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

---

<a id="callback"></a>
### callback

dimension `narrative.function` | unit `shot` | claim `interpreted` | **unverified**

A closing beat that returns to the opening image or phrase.

**Observable cues**
- Final shot or cue mirrors the first

**Measurement hints**
- pHash or text similarity between first and last shot above threshold

**Not to be confused with**
- [`cta`](#cta): A callback closes a loop; a CTA asks for an action.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

---

<a id="dim-material_atmosphere"></a>
## material_atmosphere

Temporal unit `shot`, cardinality `multi`, region-scoped.

Visible surface states and atmospheric media, especially for food: steam, condensation, moisture, haze, smoke, grain, gloss.

Measurement keys: `sheets.keyframes`, `color.specular_highlights`, `frames.noise_residual`, `frames.contrast_rms`, `motion.flow_magnitude`

<a id="steam"></a>
### steam

dimension `material_atmosphere` | unit `shot` | claim `estimated` | verified | regions `food`, `product`, `background`

Vapour plumes rising from hot food or drink.

**Aliases:** Steam; vapour

**Observable cues**
- Translucent wisps rising and dissipating

**Measurement hints**
- Low-contrast translucent region with upward, turbulent flow above the food region

**Not to be confused with**
- [`smoke`](#smoke): Smoke is denser and greyer, from burning.

**Prompt phrase:** "Gentle steam rising from the hot dish."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0178

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="condensation"></a>
### condensation

dimension `material_atmosphere` | unit `shot` | claim `estimated` | verified | regions `food`, `product`

Droplets on a cold surface (glass, bottle, fruit).

**Aliases:** Condensation; droplets; cold sweat on glass

**Observable cues**
- Small beads of water on the surface

**Measurement hints**
- Dense small specular points with dark rims on product/food surfaces

**Not to be confused with**
- [`moisture`](#moisture): Moisture is a wet sheen, not beads.

**Prompt phrase:** "Fresh condensation droplets on the cold glass."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0179

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="moisture"></a>
### moisture

dimension `material_atmosphere` | unit `shot` | claim `estimated` | verified | regions `food`, `skin`

A wet, glistening sheen on food (juicy meat, glazed vegetables, sauce).

**Aliases:** Moisture; juicy; glistening

**Observable cues**
- Glossy wet highlights

**Measurement hints**
- Broad specular highlights on food regions (color.specular_highlights)

**Not to be confused with**
- [`glossy`](#glossy): Glossy is a dry material finish.

**Prompt phrase:** "Glistening, juicy surface moisture."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0180

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="atmospheric_haze"></a>
### atmospheric_haze

dimension `material_atmosphere` | unit `shot` | claim `estimated` | verified | regions `background`, `whole_frame`

A veil in the air that lowers contrast with distance.

**Aliases:** haze; fog; Atmospheric haze; volumetric beams

**Observable cues**
- Distant planes washed out; visible air

**Measurement hints**
- Contrast decreasing with depth; raised blacks in background region

**Not to be confused with**
- [`diffusion`](#diffusion): Diffusion is an optical filter on the whole frame.

**Prompt phrase:** "Light atmospheric haze in the air."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0174, HF-0175, HF-0176

**Sources**
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Cinematic Headphones · Ultra-Realistic Ads](https://higgsfield.ai/blog/cinematic_headphones) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)
- [Nano Banana Pro Expert Use Cases](https://higgsfield.ai/blog/Nano-Banana-Pro-Expert-Use-Cases) (accessed 2026-11-01)

---

<a id="smoke"></a>
### smoke

dimension `material_atmosphere` | unit `shot` | claim `estimated` | **unverified** | regions `food`, `background`

Dense smoke from grilling, burning or a smoking effect.

**Aliases:** grill smoke

**Observable cues**
- Opaque grey-white plumes

**Measurement hints**
- Higher-opacity turbulent region than steam

**Not to be confused with**
- [`steam`](#steam): Steam is thin and quickly dissipating.

**Prompt phrase:** "Wisps of grill smoke."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Common food-film term; not in the consulted Higgsfield inventory.

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="film_grain"></a>
### film_grain

dimension `material_atmosphere` | unit `shot` | claim `measured` | verified | regions `whole_frame`

Visible granular noise in the image, film-like or sensor-like.

**Aliases:** grain; 35mm film grain; sensor grain; fine grain

**Observable cues**
- Fine dancing grain in flat areas

**Measurement hints**
- frames.noise_residual above the clean baseline, temporally uncorrelated

**Not to be confused with**
- [`macroblock_artifacts`](#macroblock_artifacts): Compression blocks are square and static.

**Prompt phrase:** "Fine 35mm film grain."

**Bindings**
- effectcraft-0.17: exact - add_effect ec.noise.addgrain
- ffmpeg: exact - noise
- higgsfield-cinema-4.0: approx - camera_model_id=<35mm Film>
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0165, HF-0166

**Sources**
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)

---

<a id="glossy"></a>
### glossy

dimension `material_atmosphere` | unit `shot` | claim `estimated` | verified | regions `food`, `product`, `background`

Surfaces with pronounced specular reflection (glazes, plates, packaging, phone glass).

**Aliases:** Glossy; polished; glaze

**Observable cues**
- Sharp mirror-like highlights

**Measurement hints**
- Compact high-intensity specular highlights on non-food materials

**Not to be confused with**
- [`moisture`](#moisture): Moisture is wetness on food.
- Matte surfaces scatter light into broad, dim highlights.

**Prompt phrase:** "Glossy, polished surface reflections."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Dictionary:** HF-0169, TX-0020

**Sources**
- [AI Product Photos](https://higgsfield.ai/blog/how-to-make-ai-product-photos-without-a-studio) (accessed 2026-11-01)
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)
- [PBRT: Roughness Using Microfacet Theory](https://www.pbr-book.org/4ed/Reflection_Models/Roughness_Using_Microfacet_Theory) (accessed 2026-11-01)

---

<a id="crispy_texture"></a>
### crispy_texture

dimension `material_atmosphere` | unit `shot` | claim `estimated` | **unverified** | regions `food`

Dry, crunchy surface micro-texture (crust, fried coating, toasted bread).

**Aliases:** crunchy; crust; micro-detail

**Observable cues**
- Fine irregular crumbs and ridges

**Measurement hints**
- High local edge density inside the food region with low specularity

**Not to be confused with**
- [`moisture`](#moisture): Moisture is smooth and shiny.

**Prompt phrase:** "Crispy golden crust with fine texture."

**Bindings**
- prompt only on: higgsfield-cinema-3.5, higgsfield-cinema-4.0, higgsfield-cinema-v2, higgsfield-kling-3.0, higgsfield-kling-4.0, higgsfield-seedance-2.5

**Verification note:** Food term; Higgsfield 'Micro-detail' is the closest documented entry.

**Dictionary:** HF-0173

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="dim-defect"></a>
## defect

Temporal unit `shot`, cardinality `multi`.

The 17 QA issues from the Codex Higgsfield inventory plus garbled_text, used to review generated or edited clips. Terms describe problems to detect; iris check reports them with frame ids.

Measurement keys: `frames.diff_prev_ssim`, `frames.L_mean`, `frames.phash`, `motion.flow_jitter`, `motion.subject_track`, `color.region_deltaE_neighbor`, `frames.sharpness_laplacian_var`, `text.tracks`, `sheets.keyframes`

<a id="identity_drift"></a>
### identity_drift

dimension `defect` | unit `shot` | claim `estimated` | verified

A recognisable face or identity changes across frames or shots.

**Aliases:** Face / identity drift; face drift

**Observable cues**
- Face shape, features or hair differ over time

**Measurement hints**
- Face-embedding distance between frames above threshold

**Not to be confused with**
- [`shot_to_shot_drift`](#shot_to_shot_drift): Shot-to-shot drift covers any appearance, not only identity.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0337

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Consistent Characters and Locations](https://higgsfield.ai/blog/consistent-characters-locations) (accessed 2026-11-01)

---

<a id="background_warping"></a>
### background_warping

dimension `defect` | unit `shot` | claim `estimated` | verified

The environment deforms unintentionally (bending walls, wobbling table).

**Aliases:** Background warping

**Observable cues**
- Straight lines bend over time

**Measurement hints**
- Non-rigid flow in static background regions

**Not to be confused with**
- [`rolling_shutter_wobble`](#rolling_shutter_wobble): Rolling shutter deforms with camera motion in a sheared pattern.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0338

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)

---

<a id="motion_morphing"></a>
### motion_morphing

dimension `defect` | unit `shot` | claim `estimated` | verified

Moving subjects change structure (a hand melts, a fork bends).

**Aliases:** morphing; Motion morphing

**Observable cues**
- Shape deformation during motion

**Measurement hints**
- Mask shape change not explained by rigid motion

**Not to be confused with**
- [`morph_transition`](#morph_transition): A morph transition is deliberate.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0339

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)

---

<a id="blending"></a>
### blending

dimension `defect` | unit `shot` | claim `estimated` | verified

Distinct identities or objects merge into one.

**Aliases:** Blending

**Observable cues**
- Two items fuse

**Measurement hints**
- Mask merge events

**Not to be confused with**
- [`duplication`](#duplication): Duplication adds copies.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0340

**Sources**
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)

---

<a id="swapping"></a>
### swapping

dimension `defect` | unit `shot` | claim `estimated` | verified

Attributes or objects change owner (shirt colours swap between people).

**Aliases:** Swapping; attribute swap

**Observable cues**
- Attribute jumps between subjects

**Measurement hints**
- Attribute track re-assigned between subject tracks

**Not to be confused with**
- [`identity_drift`](#identity_drift): Drift is gradual change of one identity.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0341

**Sources**
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)

---

<a id="duplication"></a>
### duplication

dimension `defect` | unit `shot` | claim `estimated` | verified

Unwanted extra copies of a subject or object.

**Aliases:** Duplication

**Observable cues**
- Extra hand, second fork, repeated logo

**Measurement hints**
- Object count increase without cause

**Not to be confused with**
- [`blending`](#blending): Blending merges.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0342

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)

---

<a id="scale_drift"></a>
### scale_drift

dimension `defect` | unit `shot` | claim `estimated` | verified

Relative size or proportion changes unintentionally.

**Aliases:** Scale drift

**Observable cues**
- Product grows relative to hand

**Measurement hints**
- Ratio of tracked object sizes drifts without camera cause

**Not to be confused with**
- [`apparent_push_in`](#apparent_push_in): A push-in scales everything consistently.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0343

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)

---

<a id="shot_to_shot_drift"></a>
### shot_to_shot_drift

dimension `defect` | unit `shot` | claim `estimated` | verified

Appearance changes between shots that should match (colour, props, light side).

**Aliases:** Shot-to-shot drift; continuity error

**Observable cues**
- Mismatch across a cut

**Measurement hints**
- color.region_deltaE_neighbor above tolerance; light side flips

**Not to be confused with**
- [`identity_drift`](#identity_drift): Identity drift is about faces.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0344

**Sources**
- [Consistent Characters and Locations](https://higgsfield.ai/blog/consistent-characters-locations) (accessed 2026-11-01)
- [Two Characters in One Scene](https://higgsfield.ai/blog/two-characters-one-scene-ai-video) (accessed 2026-11-01)

---

<a id="fused_hands"></a>
### fused_hands

dimension `defect` | unit `shot` | claim `estimated` | verified

Anatomical or contact errors involving hands (extra or fused fingers).

**Aliases:** Fused hands / extra fingers; extra fingers

**Observable cues**
- Wrong finger count, fused digits

**Measurement hints**
- Hand keypoint count anomalies

**Not to be confused with**
- [`duplication`](#duplication): Duplication of whole objects.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0345

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="plastic_skin"></a>
### plastic_skin

dimension `defect` | unit `shot` | claim `estimated` | verified

Skin looks synthetic and over-smoothed, without pores.

**Aliases:** Plastic skin; waxy skin

**Observable cues**
- Waxy, poreless skin

**Measurement hints**
- Very low high-frequency energy in skin regions

**Not to be confused with**
- [`diffusion`](#diffusion): Diffusion softens the whole frame deliberately.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0346

**Sources**
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="flicker"></a>
### flicker

dimension `defect` | unit `shot` | claim `measured` | verified

Unintended frame-to-frame changes in brightness or appearance.

**Aliases:** Flicker; boiling

**Observable cues**
- Brightness pulses or texture boils

**Measurement hints**
- High-frequency oscillation in frames.L_mean or local texture

**Not to be confused with**
- [`fade`](#fade): A fade is a monotonic deliberate ramp.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0347

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Kling Turbo Start/End Frame](https://higgsfield.ai/blog/A-Guide-to-Kling-Turbo-Start-End-Frame) (accessed 2026-11-01)
- [Product Formats TikTok/Reels](https://higgsfield.ai/blog/Product-Videos-TikTok-Reels-Without-Filming) (accessed 2026-11-01)

---

<a id="ghosting"></a>
### ghosting

dimension `defect` | unit `shot` | claim `estimated` | verified

Double contours or temporal trails.

**Aliases:** Ghosting

**Observable cues**
- Semi-transparent duplicate edges

**Measurement hints**
- Doubled edges offset along motion

**Not to be confused with**
- [`motion_blur`](#motion_blur): Motion blur is a continuous smear.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0348

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Script to Storyboard and Shot List](https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list) (accessed 2026-11-01)

---

<a id="jitter"></a>
### jitter

dimension `defect` | unit `shot` | claim `measured` | verified

Unintended small abrupt instability of the image or an element.

**Aliases:** Jitter; twitch

**Observable cues**
- Frame or object twitches

**Measurement hints**
- High-frequency spikes in motion.flow_jitter not matching handheld spectrum

**Not to be confused with**
- [`handheld`](#handheld): Handheld motion is smooth-ish and organic.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0349

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Direct an AI Short Film](https://higgsfield.ai/blog/Santiago-breakdown) (accessed 2026-11-01)

---

<a id="autofocus_hunting"></a>
### autofocus_hunting

dimension `defect` | unit `shot` | claim `measured` | verified

Focus searches back and forth without settling.

**Aliases:** Autofocus hunting; autofocus hunt

**Observable cues**
- Image softens and sharpens repeatedly

**Measurement hints**
- Oscillating sharpness of the same region

**Not to be confused with**
- [`rack_focus`](#rack_focus): A rack is one deliberate change.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0350

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="rolling_shutter_wobble"></a>
### rolling_shutter_wobble

dimension `defect` | unit `shot` | claim `estimated` | verified

Jello-like skew during fast motion due to sensor readout.

**Aliases:** Rolling-shutter wobble; jello

**Observable cues**
- Verticals lean during pans

**Measurement hints**
- Shear correlated with horizontal camera speed

**Not to be confused with**
- [`background_warping`](#background_warping): Warping is not tied to camera speed.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0351

**Sources**
- [Higgsfield blog: Kling 4.0 and 3.0 Prompt Guide (re-read 2026-11-01)](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="macroblock_artifacts"></a>
### macroblock_artifacts

dimension `defect` | unit `shot` | claim `measured` | verified

Visible compression blocks.

**Aliases:** Macroblock artifacts; compression blocks

**Observable cues**
- Square blocks in gradients and dark areas

**Measurement hints**
- 8x8/16x16 block boundary energy

**Not to be confused with**
- [`film_grain`](#film_grain): Grain is fine and random.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0352

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Seedance 2.5 Prompting Guide](https://higgsfield.ai/blog/seedance-2-5-prompting-guide) (accessed 2026-11-01)

---

<a id="melting_edges"></a>
### melting_edges

dimension `defect` | unit `shot` | claim `estimated` | verified

Contours dissolve or smear unintentionally.

**Aliases:** Melting edges

**Observable cues**
- Object outlines soften and drip

**Measurement hints**
- Edge sharpness loss localised on moving contours

**Not to be confused with**
- [`shallow_depth_of_field`](#shallow_depth_of_field): Defocus is depth-dependent and stable.

**Verification note:** Review vocabulary (Codex QA issue). Describes an unwanted artefact; never a desired attribute.

**Dictionary:** HF-0353

**Sources**
- [Avoid Distortions](https://higgsfield.ai/blog/how-to-avoid-distortions-ai-videos) (accessed 2026-11-01)
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="garbled_text"></a>
### garbled_text

dimension `defect` | unit `shot` | claim `measured` | **unverified**

Generated letters, numbers or logos are misspelled, malformed or change between frames.

**Aliases:** text artefacts; AI text

**Observable cues**
- Unreadable or changing characters

**Measurement hints**
- OCR content of the same text track differs across frames or has low confidence

**Not to be confused with**
- [`inscenetext`](#inscenetext): In-scene text is a technique; garbled text is its failure.

**Verification note:** Iris addition to the 17 Codex issues; the guide warns against relying on video models to preserve every letter and number.

**Sources**
- [Make AI Video Look Filmed](https://higgsfield.ai/blog/how-to-make-ai-video-look-filmed) (accessed 2026-11-01)

---

<a id="dim-style-medium"></a>
## style.medium

Temporal unit `shot`, cardinality `single`.

Rendering medium of the shot, used to route production (real capture, generation, native editor).

Measurement keys: `frames.noise_residual`, `frames.edge_density`, `color.region_palette`, `sheets.keyframes`

<a id="photorealistic"></a>
### photorealistic

dimension `style.medium` | unit `shot` | claim `estimated` | verified

Looks photographed: real light, optics and materials.

**Aliases:** live-action; Photorealistic

**Observable cues**
- Sensor noise, lens softness, physical light

**Measurement hints**
- Natural noise residual and continuous tones

**Not to be confused with**
- [`cgi_3d_render`](#cgi_3d_render): CGI shows perfect surfaces and synthetic light.

**Dictionary:** HF-0221

**Sources**
- [AI Animation Generator](https://higgsfield.ai/ai-animation-generator) (accessed 2026-11-01)
- [How to Write a Good AI Prompt](https://higgsfield.ai/creator-hub/help-center/getting-started/how-do-i-write-a-good-prompt) (accessed 2026-11-01)

---

<a id="cgi_3d_render"></a>
### cgi_3d_render

dimension `style.medium` | unit `shot` | claim `estimated` | verified

Computer-generated 3D imagery.

**Aliases:** 3D render; CGI

**Observable cues**
- Perfectly clean surfaces, idealised materials

**Measurement hints**
- Near-zero noise with smooth shading

**Not to be confused with**
- [`photorealistic`](#photorealistic): Photoreal capture has noise and imperfections.

**Dictionary:** HF-0224

**Sources**
- [AI Animation Generator](https://higgsfield.ai/ai-animation-generator) (accessed 2026-11-01)
- [Prompt Engineering — Official Higgsfield Skill](https://github.com/higgsfield-ai/skills/blob/main/higgsfield-generate/references/prompt-engineering.md) (accessed 2026-11-01)

---

<a id="motion_graphics"></a>
### motion_graphics

dimension `style.medium` | unit `shot` | claim `estimated` | verified

Animated text, shapes and diagrams as the main content.

**Aliases:** Motion graphics; 2D animation; kinetic type

**Observable cues**
- Flat shapes and type on solid or gradient backgrounds

**Measurement hints**
- Flat colour regions, sharp vector edges, no sensor noise

**Not to be confused with**
- [`screen_recording`](#screen_recording): Screen recordings show a real UI.

**Dictionary:** HF-0232, HF-0225

**Sources**
- [AI Animation Generator](https://higgsfield.ai/ai-animation-generator) (accessed 2026-11-01)
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="screen_recording"></a>
### screen_recording

dimension `style.medium` | unit `shot` | claim `estimated` | **unverified**

A capture of a real device screen or app UI, full-frame or inside a phone mockup.

**Aliases:** screen capture; app demo; UI capture

**Observable cues**
- App UI, status bar, cursor or touch indicators

**Measurement hints**
- UI text tracks with text.class = ui; pixel-exact flat regions

**Not to be confused with**
- [`motion_graphics`](#motion_graphics): Motion graphics are designed, not captured UI.

**Verification note:** Iris extension; no Higgsfield term.

---

<a id="dim-light-side"></a>
## light.side

Temporal unit `shot`, cardinality `single`.

Lateral side of the key light relative to camera (screen-left, screen-right, centred). Complements light.direction, which records front/side/top/back. Needed for continuity rules: a style can require the key to stay on one side across all shots.

Measurement keys: `light.face_luma_asymmetry`, `light.shadow_gradient_direction`, `color.region_L_percentiles`

<a id="key_screen_left"></a>
### key_screen_left

dimension `light.side` | unit `shot` | claim `estimated` | **unverified**

The brighter side of the subject is screen-left; shadows fall screen-right.

**Aliases:** key from camera-left; light from the left

**Observable cues**
- Face or object brighter on the left half; cast shadows extend to the right

**Measurement hints**
- light.face_luma_asymmetry left-right > +0.08, or shadow gradient direction pointing right

**Not to be confused with**
- [`key_screen_right`](#key_screen_right): Sign of the asymmetry is reversed.

**Prompt phrase:** "Soft key light from camera-left."

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0048, HF-0142

**Sources**
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="key_screen_right"></a>
### key_screen_right

dimension `light.side` | unit `shot` | claim `estimated` | **unverified**

The brighter side of the subject is screen-right; shadows fall screen-left.

**Aliases:** key from camera-right

**Observable cues**
- Face or object brighter on the right half; cast shadows extend to the left

**Measurement hints**
- light.face_luma_asymmetry left-right < -0.08

**Not to be confused with**
- [`key_screen_left`](#key_screen_left): Sign of the asymmetry is reversed.

**Prompt phrase:** "Soft key light from camera-right."

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0048, HF-0142

**Sources**
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="key_centred"></a>
### key_centred

dimension `light.side` | unit `shot` | claim `estimated` | **unverified**

No measurable lateral bias: light arrives from the camera axis or from directly above.

**Aliases:** frontal key; on-axis key

**Observable cues**
- Symmetric shading on the face; shadows fall behind or straight down

**Measurement hints**
- |light.face_luma_asymmetry| <= 0.08

**Not to be confused with**
- [`flat_light`](#flat_light): Centred key can still be hard and directional; flat light has no modelling at all.

**Prompt phrase:** "Frontal key light on the camera axis."

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0142

**Sources**
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="key_side_unclear"></a>
### key_side_unclear

dimension `light.side` | unit `shot` | claim `estimated` | **unverified**

Laterality cannot be determined (no face, no cast shadows, multiple sources).

**Observable cues**
- Multiple competing sources; backlit silhouette; flat graphics

**Measurement hints**
- Asymmetry metrics unavailable or contradictory across the shot

**Not to be confused with**
- [`key_centred`](#key_centred): Centred is a positive finding; unclear is an abstention.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

---

<a id="dim-material-surface"></a>
## material.surface

Temporal unit `shot`, cardinality `multi`, region-scoped.

Visible surface materials of set, props and product, used to describe environment continuity. Recorded per region (background, product, food). Appearance only; no claim about real materials.

Measurement keys: `sheets.keyframes`, `color.region_palette`, `frames.edge_density`

<a id="wood"></a>
### wood

dimension `material.surface` | unit `shot` | claim `estimated` | verified | regions `background`, `product`

Visible wood grain or warm timber surface.

**Observable cues**
- Directional grain, warm mid-tones

**Measurement hints**
- Region palette in warm hue band 20-50 deg with visible texture

**Not to be confused with**
- [`stone`](#stone): Stone shows mineral speckle, not directional grain.

**Prompt phrase:** "Natural wood surface with visible grain."

**Dictionary:** TX-0025, TX-0018

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="stone"></a>
### stone

dimension `material.surface` | unit `shot` | claim `estimated` | verified | regions `background`, `product`

Stone, marble or concrete surface.

**Observable cues**
- Mineral speckle or veining; cool or neutral tones

**Measurement hints**
- Low chroma region with mid-frequency texture

**Not to be confused with**
- [`wood`](#wood): No directional grain.

**Prompt phrase:** "Pale stone surface."

**Dictionary:** TX-0026

**Sources**
- [Food Product Video Ad](https://higgsfield.ai/blog/food-product-video-ad-ai-2026) (accessed 2026-11-01)

---

<a id="matte"></a>
### matte

dimension `material.surface` | unit `shot` | claim `estimated` | verified | regions `background`, `product`, `graphics`

Diffuse surface with subdued specular reflection.

**Observable cues**
- No sharp highlights; soft tonal transitions

**Measurement hints**
- Low highlight clipping and low specular peaks in the region

**Not to be confused with**
- [`glossy`](#glossy): Glossy shows defined reflections and highlight peaks.

**Prompt phrase:** "Matte surface, no reflections."

**Dictionary:** HF-0168

**Sources**
- [Kling 4.0 and 3.0 Prompt Guide](https://higgsfield.ai/blog/Kling-3.0-is-on-Higgsfield-User-Guide-AI-Video-Generation) (accessed 2026-11-01)

---

<a id="metal"></a>
### metal

dimension `material.surface` | unit `shot` | claim `estimated` | verified | regions `product`, `background`

Metallic surface with environment reflections.

**Observable cues**
- Reflections that describe surrounding light; cool highlights

**Measurement hints**
- High local contrast and specular peaks in the region

**Not to be confused with**
- [`glossy`](#glossy): Glossy non-metal reflects white highlights; metal tints reflections.

**Prompt phrase:** "Brushed or polished metal."

**Dictionary:** HF-0170, TX-0019

**Sources**
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="fabric"></a>
### fabric

dimension `material.surface` | unit `shot` | claim `estimated` | verified | regions `background`, `product`

Textile surface: linen, cotton, wool.

**Observable cues**
- Weave visible at close range; soft folds

**Measurement hints**
- Fine-frequency texture, low specular

**Not to be confused with**
- [`matte`](#matte): Fabric shows folds and weave.

**Prompt phrase:** "Linen fabric with visible weave."

**Dictionary:** HF-0171

**Sources**
- [AI Video Prompt Mistakes](https://higgsfield.ai/blog/ai-video-prompt-mistakes) (accessed 2026-11-01)

---

<a id="glass"></a>
### glass

dimension `material.surface` | unit `shot` | claim `estimated` | verified | regions `product`, `food`

Transparent or translucent glass.

**Observable cues**
- Refraction, transmission, rim highlights

**Measurement hints**
- Edge highlights with background visible through the region

**Not to be confused with**
- [`metal`](#metal): Glass transmits the background; metal reflects it.

**Prompt phrase:** "Clear glass with soft reflections."

**Dictionary:** TX-0024, HF-0183

**Sources**
- [Cinema Studio Prompt Guide](https://higgsfield.ai/blog/cinema-studio-3.0) (accessed 2026-11-01)

---

<a id="ceramic"></a>
### ceramic

dimension `material.surface` | unit `shot` | claim `estimated` | **unverified** | regions `product`, `food`

Glazed ceramic or porcelain (bowls, plates).

**Observable cues**
- Smooth glaze with one broad highlight

**Measurement hints**
- Single soft specular peak on a low-texture region

**Not to be confused with**
- [`glossy`](#glossy): Ceramic is a material; glossy is a finish attribute.

**Prompt phrase:** "Glazed ceramic bowl."

**Verification note:** Iris extension; common food-video prop material.

---

<a id="dim-narrative-hook_type"></a>
## narrative.hook_type

Temporal unit `sequence`, cardinality `multi`.

How the opening seconds capture attention. Interpreted from the first shots, the first text cue and the transcript; always claim_kind interpreted and reviewer-accepted.

Measurement keys: `shots.boundaries`, `text.tracks`, `audio.transcript_words`, `sheets.keyframes`

<a id="in_medias_res"></a>
### in_medias_res

dimension `narrative.hook_type` | unit `sequence` | claim `interpreted` | **unverified**

Opens inside the most intense moment, then rewinds to explain.

**Observable cues**
- First shot is the climax action; later cue states a date or setup

**Measurement hints**
- High motion energy in the first 2 s followed by a quiet card or title

**Not to be confused with**
- [`pattern_interrupt`](#pattern_interrupt): In medias res is narrative order; pattern interrupt is a visual shock.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0272

---

<a id="direct_question"></a>
### direct_question

dimension `narrative.hook_type` | unit `sequence` | claim `interpreted` | **unverified**

Opens with a question addressed to the viewer.

**Observable cues**
- Question mark in the first text cue or rising intonation in the first sentence

**Measurement hints**
- text.tracks first cue contains '?' or transcript first sentence is interrogative

**Not to be confused with**
- [`bold_claim`](#bold_claim): A claim asserts; a question asks.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0272

---

<a id="bold_claim"></a>
### bold_claim

dimension `narrative.hook_type` | unit `sequence` | claim `interpreted` | **unverified**

Opens with a strong assertion or a number.

**Observable cues**
- Declarative first cue, often with a figure

**Measurement hints**
- First cue is declarative and short (<= 8 words)

**Not to be confused with**
- [`direct_question`](#direct_question): No question form.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0272

---

<a id="pattern_interrupt"></a>
### pattern_interrupt

dimension `narrative.hook_type` | unit `sequence` | claim `interpreted` | **unverified**

Opens with a visual or sonic shock unrelated to the topic.

**Observable cues**
- Abrupt cut, flash or loud sound in the first second

**Measurement hints**
- Motion or audio energy peak at t < 1 s

**Not to be confused with**
- [`in_medias_res`](#in_medias_res): Pattern interrupt is sensory, not narrative.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0272

---

<a id="visual_curiosity"></a>
### visual_curiosity

dimension `narrative.hook_type` | unit `sequence` | claim `interpreted` | **unverified**

Opens on an unexplained object or action that invites a question.

**Observable cues**
- Close shot of something ambiguous; no text yet

**Measurement hints**
- First text cue appears after t > 1.5 s

**Not to be confused with**
- [`pattern_interrupt`](#pattern_interrupt): Curiosity is quiet; interrupt is loud.

**Verification note:** Iris extension added 2026-11-01 for the Style Bible contract.

**Dictionary:** HF-0272

---
