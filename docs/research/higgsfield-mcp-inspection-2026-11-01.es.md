# Inspección de solo lectura del MCP de Higgsfield — 2026-11-01

Sesión: Claude Code (desktop), servidor MCP conectado `mcp.higgsfield.ai` (id interno `1b4c3f94-…`).
Nada se generó. Todas las cifras salen de `balance`, `models_explore` y `generate_video/generate_image` con `get_cost: true`.
Las cotizaciones pueden cambiar por cuenta, plan, fecha y parámetros; volver a cotizar antes de cada lote.

## 1. Cuenta observada

| Campo | Valor |
|---|---|
| `credits` | 1.7 |
| `subscription_plan_type` | `free` |
| `unlim.available` | false |

Consecuencia: con esta cuenta no se puede ejecutar ninguna receta (la más barata cuesta 5 créditos). El escenario de 3000 créditos/mes de los informes corresponde a Ultra (129 USD/mes según blog oficial del 24 oct 2026), que no está contratado.

## 2. Herramientas reales del MCP (nombres observados)

Generación: `generate_video`, `generate_video_batch`, `generate_image`, `generate_image_batch`, `generate_audio`, `generate_3d`, `motion_control`, `reframe`, `upscale_video`, `upscale_image`, `remove_background`, `outpaint_image`, `dubbing`, `voice_change`.
Descubrimiento y estado: `models_explore` (list/search/get/recommend), `balance`, `transactions`, `jobs_wait` (máx 15 s por llamada, 1–12 jobs), `show_generations`, `show_generation_by_ids`, `show_result`.
Media: `media_upload` → PUT → `media_confirm`; `media_import_url`; `media_upload_widget`.
Presupuesto y planes: `show_plans_and_credits`, `cancel_trial_auto_renewal`.
Workflows/skills del propio servidor: `get_workflow_instructions`, `get_workflow_bundle_file`, `get_presets`, `execute_preset`, `get_preset_instructions`.
Otros: `video_analysis_create/status/jobs`, `virality_predictor`, `sandbox_exec`, Ads Studio, Marketing Studio, Shorts Studio, 3D Scene Builder, TikTok publish, websites.

Los nombres `higgsfieldmcp_balance`, `higgsfieldmcp_animation_actions`, `higgsfieldmcp_apps_search` del PDF de 23 páginas NO existen en este servidor. Sí existe `animation_actions` y `apps_search` sin prefijo.

Comportamientos declarados en el esquema de `generate_video`:
- `get_cost: true` cotiza sin enviar job.
- `aspect_ratio` es parámetro MCP; Marketing Studio por defecto es 16:9, pasar `9:16` siempre.
- `medias[].value` debe ser `media_id` o `job_id`, nunca URL.
- Ante timeout de transporte NO reenviar; reutilizar job id.
- `use_unlim` / `use_free_gens` existen; omitidos, el servidor puede devolver `unlim_choice` antes de cobrar.
- `count` 1–4 solo para variantes del mismo prompt; batch para peticiones independientes.
- Defaults declarados: `seedance_2_5` video general, `kling3_0` multi-shot/audio/motion transfer, `marketing_studio_video` producto/ads, `minimax_h3` keyframes 2K, `gpt_image_2_5` imagen general.

## 3. Catálogo observado

58 modelos de video, 49 de imagen (`has_more: false`). Modelos relevantes para las cinco recetas:

| id | Duración | Resoluciones | Roles de media | Notas |
|---|---|---|---|---|
| `seedance_2_5` | 4–30 s (default 5) | 480p/720p/1080p | start_image, end_image, image_references, video_references, audio_references | modos t2v / omni_reference / video_edit / video_extension; `draft` 480p finalizable 7 días; `generate_audio` default true |
| `kling3_0` | 3–15 s | mode std/pro/4k | start_image, end_image | `sound` on/off; soporta unlim |
| `kling4_0` | (ver get) | 720p/1080p | start_image, end_image, image_references, video_references | modos text-to-video / image-to-video / reference-to-video / video-edit; `kling_element_ids` |
| `kling_o3_flf` | — | std/pro/4k | start_image, end_image | Kling 3.0 Omni primer/último frame; `multi_shots`, `multi_prompt` |
| `kling_o3_image_reference` | — | std/pro/4k | image_references | Omni por referencias |
| `hf_mult_replace_object` | — | 480p/720p/1080p | image_references, video_references | Genjutsu Object Swap; exige al menos 1 imagen + 1 video para cotizar |
| `hf_mult_motion_control` | — | 480p/720p/1080p | image_references, video_references | Genjutsu Motion Transfer; hay variantes `_flash` (Lite) |
| `cinematic_studio_video_4_0` | — | 480p/720p/1080p | start/end/image/video/audio refs | `camera_model_id`, `camera_lens_id`, `camera_aperture_id`, `pacing_id`, `genre_id`, `light`, `color_palette` |
| `cinematic_studio_video_3_5` | — | 480p/720p/1080p | idem | `camera_style`, `light_scheme`, `color_grading` como enums |
| `seedance_2_0` / `seedance_2_0_mini` | — | hasta 4k / 720p | refs completos | soportan unlim |
| `wan2_7` | — | 720p/1080p | start_image, end_image, audio_references | soporta unlim |
| `minimax_h3` | 4–15 s | 2K | refs completos | recomendado por el servidor para I2V macro |
| `reframe` | — | 480p/720p/1080p | video_references, start_image | herramienta aparte para pasar a 9:16 |
| Post: `topaz_video`, `bytedance_video_upscale`, `video_deflicker`, `fps_boost`, `sam_3_video` | | | | |

Imagen: `nano_banana_pro` (1k/2k/4k), `nano_banana_2`, `gpt_image_2_5` (quality low…max, `background: transparent`), `seedream_v5_pro` (2k, `remove_bg`, `is_inpaint`), `soul_2`, `flux_3_image`, `ideogram_4_5`, `ideogram_vector` (SVG), `recraft_v4_1` (vector/utility, paleta `#RRGGBB`), `image_decompose` (capas), `3d_jutsu_angles`, `topaz_image`.

## 4. Cotizaciones observadas (créditos por intento, `get_cost: true`)

| Configuración | Créditos |
|---|---|
| Seedance 2.5 · 5 s · 480p · draft | 15 |
| Seedance 2.5 · 5 s · 720p · sin audio (t2v u omni_reference) | 35 |
| Seedance 2.5 · 5 s · 1080p · sin audio | 80 |
| Seedance 2.0 · 5 s · 720p · fast · sin audio | 12.5 |
| Kling 3.0 · 5 s · std · sin sonido | 7.5 |
| Kling 3.0 · 5 s · std · con sonido | 10 |
| Kling 3.0 · 5 s · pro · sin sonido | 8.75 |
| Kling 3.0 · 5 s · 4k · sin sonido | 30 |
| Kling 3.0 Omni Frames (`kling_o3_flf`) · 5 s · std · sin sonido | 5 |
| Kling 4.0 · 5 s · image-to-video · 720p | 11.25 |
| Kling 4.0 · 5 s · image-to-video · 1080p | 16.25 |
| Cinema Studio 4.0 · 5 s · 720p · sin audio | 35 |
| Wan 2.7 · 5 s · 720p | 7.5 |
| Genjutsu replace · 720p | no cotiza sin medias (`missing_roles: image, video`) |
| Nano Banana Pro · 2k | 2 |
| Seedream 5.0 Pro · 2k | 2.5 |
| Soul 2.0 · 2k | 0.12 (se muestra como 1) |
| GPT Image 2.5 · 1k · low | 0.25 |

Confirmaciones frente a los documentos: Seedance 2.5 35/80 (blog oficial y Manual v2.0) correcto. Kling 3.0 std sin sonido 7.5 en MCP frente a 8.75 observado en el cotizador web (Manual E01); el 8.75 corresponde a `pro`. Nano Banana Pro 2 correcto. El "0.125 por still" del PDF de 23 págs solo se cumple con Soul 2.0 (0.12), no con Nano Banana Pro.

## 5. Presupuesto recalculado con cotizaciones MCP (reserva 20 %, 2400 operativos sobre 3000)

| Receta | Modelo propuesto | Créditos/intento | 75 assets × 2 intentos |
|---|---|---|---|
| R1 macro comida (I2V) | Kling 4.0 I2V 720p | 11.25 | 1687.5 |
| R1 alternativa | Kling 3.0 std, sin sonido | 7.5 | 1125 |
| R2 fondo para hero de app | Kling 3.0 std | 7.5 | 1125 |
| R3 arco de cámara | Kling 4.0 I2V 720p | 11.25 | 1687.5 |
| R4 inserto conceptual | Seedance 2.5 720p | 35 | 5250 (no cabe) |
| R4 alternativa | Seedance 2.0 fast 720p | 12.5 | 1875 |
| R5 transición primer/último frame | Kling 3.0 Omni Frames std | 5 | 750 |

Mezcla viable con 2400 operativos: 30 R1/R3 en Kling 4.0 (675) + 15 R2/R5 en Kling 3.0/Omni (≈190) + 15 R4 en Seedance 2.0 fast (375) + 15 gráficos nativos en EffectCraft (0) ≈ 1240 a dos intentos, con margen para referencias (≈2 por still) y una tanda Seedance 2.5 de prueba.

## 6. Pendiente tras esta inspección

- Plan y créditos: la cuenta está en `free` con 1.7 créditos. Sin suscripción no hay piloto posible.
- Cotizar Genjutsu con medias reales (exige imagen + video).
- Verificar con `models_explore get kling4_0` el rango de duración (no aparece en `list`).
- Cargar una referencia real de plato por `media_upload` y cotizar `omni_reference` con medias para confirmar que el precio no cambia.
- Probar `reframe` para 9:16 frente a pedir `aspect_ratio: 9:16` en origen.
- Confirmar integración de archivos en EffectCraft 0.17.0 (`file.import`) con un clip descargado.
