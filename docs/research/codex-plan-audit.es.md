# Auditoría del paquete Codex "Iris Creative" (2026-11-01)

Archivos auditados: `Iris_Creative_Implementation_Plan.md` (398 líneas), `Higgsfield_Prompt_Engineering_Guide.md` (1131 líneas, 548 entradas de terminología), `README_Iris_Research.md`, `Higgsfield_Taxonomy.json` (estructura y campos), `Contexto_operativo_Calorico.md`. Se contrastan con tres fuentes que el paquete no tuvo: SISTEMA.md (contrato real del pipeline), el inventario y las cotizaciones reales del MCP de Higgsfield obtenidas hoy, y las restricciones documentadas de Grok Bot.

Veredicto corto: el plan de Codex es **arquitectónicamente superior** al mío en el modelo de evidencia, la contabilidad de cobertura y el rigor temporal. Es **más débil** en integración con lo que ya existe, omite el audio, no cierra el ciclo sobre clips generados y no presupuesta la revisión humana. La taxonomía de 548 entradas es un vocabulario de **generación**, no de **percepción**. Recomiendo fusionar: contratos de Codex + puntos de integración y compuerta de mi plan.

---

## 1. Lo que Codex hace mejor (adoptar tal cual)

| Punto | Por qué es mejor | Qué corrige de mi plan |
|---|---|---|
| **Tres ejes de cobertura** (decodificación, medición, exposición al modelo) | Separa "medí cada frame" de "el VLM vio cada frame". Enviar el MP4 a un modelo no es evidencia de exposición frame a frame. | Mi criterio único "filas = nb_read_frames" solo cubría el primer eje. |
| **Línea de tiempo por PTS, no `frame_idx / fps`** | VFR, frames duplicados, B-frames retrasados y metadatos de rotación rompen la aritmética simple. Intervalos semiabiertos `[start, end)`. | Mi `t_s = frame_idx / fps` es incorrecto para VFR y para el MOV HLG a 60 fps del caso Messi. |
| **Cuatro capas de movimiento** (cámara aparente, sujeto, transformación editorial, gráfico) | Un zoom digital en edición, un crop animado y un dolly real producen flujo parecido. Etiqueta `apparent_push_in` con alternativas en lugar de afirmar mecanismo. | Yo tenía dos capas y clasificaba `push_in` como hecho. |
| **Tipos de afirmación** `measured / estimated / interpreted / designed` + `review_status` independiente + confianza `null` si no está calibrada | Impide que una estimación aceptada se convierta en medición y que un 0,86 inventado parezca probabilidad. | Mi ejemplo de etiqueta llevaba `confidence: 0.86` sin calibración. |
| **Análisis de referencia separado de dirección adaptada a marca** | Una referencia con cinco looks incoherentes no se reescribe como coherente; la elección va al registro de adaptación. | Mi `guideline.json` mezclaba ambos. |
| **Color por región comparable** (fondo, comida, piel, UI, gráficos), no histograma global | "Una ensalada verde y una interfaz blanca no deben compartir el mismo porcentaje de verde." | Mi ΔE2000 plano-vs-mediana global penalizaría cualquier corte entre comida y pantalla de la app. |
| **Luz como atributos separados** (dirección, dureza de borde, contraste, rim, sombra de contacto) con `claim_kind: designed` para lux, Kelvin, milímetros y apertura | No se pueden recuperar de un video editado; se eligen como parámetros de producción. | Coincide con mis proxies, pero lo formaliza mejor. |
| **Eventos cortos conservados** (flash de un frame, caption de un frame) en una ruta paralela a PySceneDetect | El filtro de duración mínima de escena suprime insertos brevísimos. | No lo tenía. |
| **Gestión de color explícita** (primarias, transferencia, rango; HDR aparte de derivado SDR) | Necesario para comparar fuentes; el caso Messi venía en HLG BT.2020. | No lo tenía. |
| **Presupuesto de recursos concreto** (1 job pesado, 4 hilos, worker < 4 GB, buffer 8–32 frames, reserva de disco 15 GB; 11,2 GB de píxeles crudos por minuto) | Evita que un `np.stack` de todo el video mate la VM. | Mi "256 px, 1–2 min" era una estimación sin límites de memoria. |
| **Trabajos reanudables con checkpoints por etapa y ventana** | La VM de Grok Bot puede reiniciarse a mitad de un análisis. | Lo tenía implícito, no diseñado. |
| **Reglas de hallazgo sobre nombres opacos** (3D Rotation gira el producto, Lazy Susan gira la cámara; Hero Cam es órbita rápida; Buckle Up es vista desde abajo a través de suelo transparente) | El bot no debe inferir comportamiento de un preset por su nombre en inglés; debe recuperar la definición. | No lo tenía. |
| **No dar fechas antes del piloto** | Las etapas caras (OCR, VLM) no están medidas. | Mi tabla de seis semanas era prematura; mantener un piloto acotado en tiempo, no un calendario de entregas. |

## 2. Fallos y vacíos del plan de Codex

### 2.1 Independencia del repositorio: un error de alcance, no una virtud
El plan declara que "el repositorio de marketing existente no es la base arquitectónica" y construye `BrandVisualSpec` con `brand_id: example_brand`. Pero el propio paquete Codex, en `Contexto_operativo_Calorico.md`, reconoce que SISTEMA.md define 1080×1920 a 30 fps, blanco `#FFFFFF`, coco `#F4EDDF`, carbón `#2B2B2B`, acento `#9E7852`, Inter 400/600/700, subtítulos 52 px, zona segura 240/660/300/60 y audio −14 LUFS. Nada de eso aparece en el plan en inglés. Un grep del plan por `G1`, `etiqueta_ia`, `tokens.json`, `Grok Bot`, `/workspace`, `LUFS`, `whisper`, `audio`, `beat` devuelve cero resultados.

Consecuencias:
- **La compuerta G1 del pipeline falla si `etiqueta_ia` es verdadera** ("Calorico no usa arte generado"). El `Contexto_operativo` lo dice; el plan de implementación lo ignora. Cualquier asset generado que Iris produzca hoy no puede entrar en la pieza publicada. Esto hay que resolverlo en el contrato antes de la Fase 2, y el plan no lo menciona.
- El QC existente ya mide `fondo_tokens`, `fondo_oscuro`, `colores`, `zona_segura`, `subtitulos`, `silencios`, `congelados`. Iris reinventaría parte de eso en lugar de endurecerlo con rangos aprendidos.
- Ya existen `content_id`, `designs.csv`, `design_preferences.csv` y el selector Thompson. El "aprendizaje de preferencia de marca" que Codex describe en §11 ya tiene un lugar en el repo; el plan no lo conecta.

### 2.2 Taxonomía sesgada a generación, no a percepción
De las 548 entradas: 263 `cinematic`, 94 `preset_label`, 48 `workflow`, 25 `prompt_section`, 17 `qa_issue`, 13 `ui_value`, 8 `api_parameter`. Solo 40 son extensiones Iris (tipografía y animación) y la taxonomía Iris original (4 operaciones × 6 dominios × 43 técnicas de composición) **no está en el JSON**. La guía la cita conceptualmente pero el registro machine-readable no la incluye. Resultado: el bot tendrá vocabulario rico para escribir prompts y pobre para describir *qué hace* una imagen (aislamiento, figura-fondo, líneas guía, marco dentro del marco). Las entradas carecen de `observable_cues`, `counterexamples`, `temporal_unit` y `bindings`, lo que el propio plan admite como trabajo pendiente.

### 2.3 Sin etapa de audio
No hay LUFS, detección de habla/música, transcripción, cadencia de palabras ni alineación corte-beat. SISTEMA.md ya tiene `faster-whisper`, `ebur128` y `silencedetect` en el runner. La sincronía subtítulo-voz (que Codex sí menciona en Stage F como "against speech where available") no puede medirse sin transcripción. "Profesional" incluye que los cortes caigan en el ritmo y que las captions vayan con la voz.

### 2.4 No hay compuerta de continuidad sobre footage nuevo
`iris validate PACKAGE_ID` valida parámetros contra el registro de capacidades. `continuity_report.json` describe la referencia. Falta la operación que toma un clip candidato (propio o de Higgsfield) y lo evalúa contra la dirección aprobada. Sin eso, la Fase 1 produce documentos pero no decide nada sobre lo que entra al montaje.

### 2.5 Coste de la interpretación con VLM sin cota
Ventanas de 16–32 frames con solape de 8 → ~75 ventanas por minuto de video, cada una con hasta 32 imágenes. El plan dice "estimar antes de correr" pero no fija un modo por defecto. Con la cuota semanal de Grok Bot desconocida y sin plan Ultra en Higgsfield (cuenta observada: free, 1.7 créditos), el modo estricto debe ser opt-in y el modo economía (hojas de contacto + keyframes por plano) el predeterminado. Además no se verificó que la visión de Grok acepte secuencias ordenadas de 32 imágenes.

### 2.6 Realidades de la VM de Grok Bot no tratadas
El plan describe "una máquina Linux de 8 núcleos y 15 GB" pero no dice que es la VM del bot ni asume sus reglas: paquetes temporales reemplazables, recuperaciones que interrumpen trabajo, `/workspace` como única persistencia, VM compartida entre bots de la misma cuenta. SQLite con "un escritor coordinado" en una VM compartida necesita bloqueo explícito. La instalación debe ser idempotente y `doctor` debe correr al inicio de cada skill.

### 2.7 Revisión humana sin presupuesto
Cada afirmación incierta o consecuente va a cola de revisión. SISTEMA.md tiene una regla: si `hours.csv` supera 12 horas semanales, el informe propone modo mínimo. El plan no estima minutos de revisión por referencia ni define qué se aprueba en bloque. Riesgo real de que Iris muera por fatiga del revisor.

### 2.8 Hito 0 contradictorio
El hito 0 exige "20–30 referencias representativas y clips diagnósticos controlados" antes de ingestar nada; el §13 dice empezar con una referencia de 30–60 s. Recomendación: una referencia primero, corpus después.

### 2.9 Faltan dos detectores baratos que sí importan
Deduplicación por hash perceptual (la lección del "Editor V2": 30 imágenes usadas 75 veces) y detección de reutilización de planos. Ambos cuestan nada en CPU y describen el estilo de montaje mejor que muchas etiquetas.

### 2.10 Idioma
Todo en inglés es correcto para IDs de taxonomía y prompts. Pero la lista prohibida ES-MX, los captions, los guiones y el revisor están en español. `report/index.html` y las definiciones mostradas al revisor deberían tener versión en español; los `term_id` permanecen en inglés.

## 3. Comprobaciones contra el MCP real (hoy)

| Afirmación de la guía Codex | Observado en el MCP |
|---|---|
| `aspect_ratio` ausente del esquema Kling I2V; presente en playground de Cinema Studio | En el MCP, `aspect_ratio` es parámetro general de `generate_video`; `kling4_0` lista `21:9, 16:9, 9:16, 1:1, auto`. El MCP sí lo expone. |
| Kling 4.0: 3–30 s, 720p/1080p, `image_urls` intermedios, `end_image_url` | MCP `kling4_0`: roles `start_image, end_image, image_references, video_references`; modos `text-to-video / image-to-video / reference-to-video / video-edit`; 720p/1080p. Coincide en lo esencial; los nombres de rol difieren de los campos REST, como advierte la guía. |
| `negative_prompt` no universal | Ningún modelo del catálogo MCP expone `negative_prompt`. Correcto. |
| 65 Camera Controls del catálogo público | No son parámetros del MCP. `cinematic_studio_video_4_0` expone `camera_model_id`, `camera_lens_id`, `camera_aperture_id`, `pacing_id`, `genre_id`, `light`, `color_palette`; `cinematic_studio_video_3_5` expone `camera_style` con 9 enums (`classic_static, silent_machine, one_take, epic_scale, intimate_observer, impossible_camera, documentary_snap, raw_chaos, dreamy_flow`), `light_scheme` con 6 y `color_grading` con 8. Estos enums son los `target_binding` reales que la taxonomía debe mapear. |
| Nano Banana naming trap (`nano_banana_flash` = NB2) | En el MCP existen `nano_banana`, `nano_banana_pro`, `nano_banana_2`, `nano_banana_2_1`, `nano_banana_2_lite`, `nano_banana_2_shots`. La trampa confirma la regla: guardar display name, alias CLI e id MCP por separado. |
| Cinema Studio web: 50 referencias; CLI: 30 | No verificable por MCP sin enviar; `cinematic_studio_video_4_0` acepta `image_references` sin `max` declarado en `list`. Pendiente con `models_explore get`. |
| Costes | Cotizaciones reales hoy: Kling 3.0 std sin sonido 7.5; Kling Omni Frames 5; Kling 4.0 I2V 720p 11.25 / 1080p 16.25; Seedance 2.5 720p 35 / 1080p 80 / draft 15; Cinema Studio 4.0 720p 35; Wan 2.7 7.5; Nano Banana Pro 2; GPT Image 2.5 low 0.25; Soul 2.0 0.12. La guía no tiene ninguna cifra; el compilador de Codex debe leer estas del registro de capacidades, no de blogs. |

## 4. Fusión recomendada

**Del plan de Codex, sin cambios:** modelo de afirmaciones (§6), tres ejes de cobertura (§3), índice por PTS y buffers acotados (Stage B), cuatro capas de movimiento (Stage E), color regional y gestión de color (Stages C y G), eventos cortos (Stage D), separación análisis / dirección (§1), presupuesto de recursos (§9), trabajos reanudables (§8), estrategia de validación con fixtures (§14), regla de no inferir presets por nombre.

**De mi plan, añadir:**
1. `brand_envelope` generado desde `brand/tokens.json` real, no un ejemplo. Estilos como perfiles dentro del sobre.
2. Etapa de audio: `ebur128`, habla/música, `faster-whisper`, onsets, alineación corte-beat, sincronía caption-voz.
3. `iris check <clip> --against <direction>`: la compuerta sobre footage nuevo, con `pass / warn / fail` por regla y frame.
4. pHash y reutilización de planos.
5. Integración por archivos con el repo: Iris escribe JSON Schema 2020-12 que `qc.ts`, `rubric.ts` y `pickDesignVariant` pueden leer. Nada se reescribe.
6. Skills de Grok Bot ("Analizar referencia", "Comprobar clip"), `doctor` al inicio, instalación idempotente, estado solo en `/workspace`, bloqueo de SQLite.
7. Modo economía por defecto para el VLM (hojas de contacto paginadas + keyframes por plano); modo estricto opt-in con coste cotizado antes.
8. Presupuesto de revisión humana: minutos por referencia medidos en el piloto; aprobación en bloque de afirmaciones `measured`; revisión individual solo de `estimated` e `interpreted` consecuentes.

**Decisión previa a todo:** resolver en SISTEMA.md qué significa `etiqueta_ia` cuando el asset IA es B-roll complementario y la pantalla y la voz siguen siendo reales. Sin esa decisión, la Fase 2 no puede publicar nada y la Fase 1 solo produce documentos.

**Taxonomía:** mantener el registro de 548 entradas de Codex como `generation_vocabulary` (sirve al compilador de prompts y al `target_binding`). Crear aparte `perception_taxonomy` con Iris (4 × 6 × 43) más la capa temporal, cada término con `observable_cues`, `counterexamples`, `temporal_unit` y `measurement_keys`. Son dos registros con mapeos explícitos (`exact / narrower / broader / related`), no uno.

**Secuencia:** piloto acotado a dos semanas con una sola referencia de 30–60 s (comida + persona + texto + varios planos), midiendo decodificación, OCR, flujo, VLM, RAM pico, disco, coste y minutos de revisión. Solo después, hitos con fechas.
