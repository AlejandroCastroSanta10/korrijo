# Prompts del pipeline — fase de transcripción

Este documento registra el diseño y la evolución del prompt que usa la fase de
transcripción (`app/pipeline/transcription.py`) para convertir un examen
manuscrito en una transcripción estructurada (`StructuredTranscription`).

El modelo de referencia durante el desarrollo ha sido **qwen3-vl:8b** servido por
Ollama en local (mismo modelo del PoC). Las observaciones sobre comportamiento
del modelo son específicas de esa familia; otros VLM pueden comportarse distinto.

---

## v0 — Prompt del PoC con `format="json"`

Punto de partida: el script exploratorio `scripts/pipeline_poc/transcribe.py`.
Pedía un JSON con cuatro secciones (`exam`, `metadata`, `questions`, `answers`)
y forzaba salida estructurada con el parámetro `format="json"` de Ollama.

**Problema observado (PoC):** con qwen3-vl, `format="json"` hace que el modelo
entre en modo *thinking* y devuelva **contenido vacío**. La salida estructurada
nativa de Ollama no es usable con este VLM.

## v1 — Sin `format`, con `/no_think` y extracción por regex

Solución adoptada en el PoC:

- Quitar `format="json"`.
- Pedir el JSON **en el propio prompt** y añadir la directiva `/no_think` para
  desactivar el bloque de razonamiento.
- Extraer el primer objeto JSON de la respuesta con regex y limpiar bloques
  `<think>...</think>` que el modelo cuela aun así.

**Resultado (PoC, `examen_prueba.jpeg`):** transcripción buena. Casi todo el texto
manuscrito se identifica bien; se respetan letras de distinto tamaño, torceduras,
tachones y guiones de fin de línea (los une con la palabra siguiente).

**Limitación observada:** una corrección tachada con una línea horizontal no se
contempló: el modelo transcribió la palabra tachada en lugar de la corregida.
De ahí la instrucción explícita sobre tachados en la versión actual.

## v2 — Esquema reorientado a la corrección (versión adoptada)

Al integrar la fase en el pipeline real cambió el objetivo del JSON. El PoC
extraía también el enunciado y la puntuación de cada pregunta, pero esa
información ya la aporta la rúbrica y el examen modelo (gold standard) en fases
posteriores. La transcripción solo necesita **qué respondió el alumno** y **a qué
pregunta corresponde**, más los datos de cabecera.

Cambios respecto a v1:

- Esquema simplificado a dos claves: `metadata` y `answers`.
- `metadata` con los campos de cabecera reales de un examen:
  `nombre`, `apellidos`, `grupo`, `fecha`, `dni`. Todos opcionales (null si no
  aparecen): no todos los exámenes los llevan.
- Cada respuesta es `{ question_number, answer_text, notes }`. `question_number`
  es entero; `answer_text` se transcribe literal (sin corregir ortografía).
- Campo `notes` para que el modelo marque los **casos límite** en lugar de
  inventarse contenido o descartar la respuesta:
  - pregunta en blanco → `answer_text: ""` + nota "en blanco",
  - respuesta ilegible → transcribir lo posible + nota,
  - varias preguntas en una página → respuestas separadas,
  - respuesta partida entre páginas → unirla en un `answer_text`.
- Instrucción explícita sobre tachados (resuelve la limitación de v1).
- Se mantiene `/no_think` y la ausencia de `format`, por lo aprendido en v0/v1.

### Hallazgo al validar v2 contra el examen real: `think=False` en la API

Al ejecutar v2 contra `examen_prueba.jpeg` con qwen3-vl, el modelo devolvía
**`content` vacío** en todos los intentos, pese al `/no_think` del prompt. La
causa: el cliente de Ollama (0.6.x) tiene un parámetro `think` que por defecto
es `None`; con un modelo de razonamiento híbrido como qwen3-vl eso hace que todo
el texto se vaya al campo `message.thinking` y `message.content` quede vacío.

Comprobado con un diagnóstico de una sola llamada:

| `think` | `content` | `thinking` | resultado |
|---------|-----------|------------|-----------|
| `None` (defecto) | vacío | lleno | inservible |
| `False` (explícito) | JSON válido (1311 chars) | lleno | correcto |

El `/no_think` del prompt **no** desactiva el razonamiento por sí solo; lo que
arregla la salida es pasar `think=False` a `chat()`. Por eso
`OllamaVLMProvider` usa `think=False` por defecto (constructor parametrizable).
Con ese cambio, `content` trae el JSON limpio y la transcripción del examen real
es fiel (nombre, apellidos, grupo, fecha y respuestas literales).

#### Intentos vacíos residuales y `num_ctx` como palanca

Incluso con `think=False`, qwen3-vl **no deja de razonar del todo** (el campo
`thinking` sigue trayendo bastante texto). Es no determinista: de vez en cuando
una pasada agota su presupuesto razonando y devuelve `content` vacío. No es un
fallo: es justo el caso que cubre `max_retries` en `transcribe_exam`, que vuelve
a llamar y normalmente acierta en el siguiente intento (se ve como un log
WARNING "respuesta vacía", no como una excepción).

Decisión: **se deja con los reintentos tal cual**. Subir `num_ctx` (p. ej. de
8192 a 16384) daría más margen al razonamiento y podría reducir esos intentos
vacíos, pero es una conjetura no verificada que cuesta memoria/latencia y no
garantiza eliminarlos. `num_ctx` queda anotado aquí como punto de ajuste
conocido: si en uso real (lotes de exámenes) los intentos vacíos resultan
frecuentes, medir y entonces decidir entre subir `num_ctx`, retocar el prompt o
cambiar de modelo/proveedor. Optimizar sobre evidencia, no sobre corazonada.

El prompt final adoptado vive como constante `TRANSCRIPTION_PROMPT` en
`app/pipeline/transcription.py` (única fuente de verdad; este documento explica
el porqué, no lo duplica).

### Parsing robusto en lugar de confiar en salida limpia

Como no se usa `format`, la salida del modelo puede traer ruido. El parser
(`_parse_json_object`) tolera, en este orden:

1. bloques `<think>...</think>`,
2. vallas de código markdown ```` ```json ```` ,
3. preámbulos o texto alrededor del JSON (extrae el primer objeto balanceado),
4. comas finales antes de `}`/`]` y comillas tipográficas como delimitadores.

Si aun así no parsea, `transcribe_exam` reintenta (`max_retries`, por defecto 2)
y, agotados los intentos, lanza `TranscriptionError` con log de cada fallo.

---

## Validación empírica

La evolución v0 → v1 está respaldada por las ejecuciones del PoC
(ver `docs/pipeline-poc.md`). El esquema v2 se ha **validado contra el examen
real** `examen_prueba.jpeg`: tras el ajuste `think=False`, la transcripción es
fiel y parseable. Lo comprueba de forma reproducible el test de integración
`tests/pipeline/test_transcription.py::test_transcripcion_examen_real`
(se salta si no hay Ollama/modelo). Forma de reejecutarlo:

```bash
# Requiere Ollama corriendo y PIPELINE_VLM_MODEL configurado en .env
pytest tests/pipeline/test_transcription.py -m integration -s
```

Si la transcripción del examen real no fuera lo bastante fiel, iterar aquí el
prompt (criterios de cada pregunta, manejo de tachados, etc.) y anotar el
resultado en una nueva sección de este documento.
