# Prompts del pipeline

Este documento registra el diseño y la evolución de los prompts del pipeline de
corrección. Tiene dos partes: la **fase de transcripción**
(`app/pipeline/transcription.py`) y la **fase de corrección**
(`app/pipeline/grading.py`).

---

# Fase de transcripción

Convierte un examen manuscrito en una transcripción estructurada
(`StructuredTranscription`).

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

## v3 — Refinamiento de fidelidad OCR (versión adoptada)

La transcripción es el cuello de botella de calidad del sistema: si la respuesta
manuscrita del alumno se extrae mal, la corrección posterior arranca de datos
erróneos. Se refuerza el prompt v2 **sin tocar el esquema** (`metadata` + `answers`
con `question_number` entero), enfocándolo en fidelidad:

- **Cifras, unidades, símbolos y fórmulas exactos.** En muchos exámenes la rúbrica
  puntúa valores concretos ("120/80 mmHg", "≥140/90", "30:2"); un dígito o símbolo
  cambiado falsea la corrección. Se pide copiarlos con precisión.
- **No inventar + marcador `[ilegible]`.** v2 decía "transcribe lo que puedas". v3
  prohíbe explícitamente sustituir lo ilegible por una palabra plausible
  (alucinación) y pide marcarlo inline como `[ilegible]` y anotarlo en `notes`.
- **Solo lo manuscrito, no el enunciado impreso.** Evita que `answer_text` se
  contamine con el texto preimpreso de la pregunta; el enunciado solo sirve para
  saber a qué pregunta corresponde cada respuesta.
- **Texto intercalado.** Incorporar lo escrito en márgenes, entre líneas o señalado
  con flechas, en el punto donde el alumno lo intercala.
- **Numeración robusta.** Respuestas sin numerar → correlativas por orden de
  lectura; apartados (1a, 1b...) → una sola respuesta conservando las marcas (el
  esquema mantiene `question_number` entero).
- **Dibujos/esquemas** → descripción breve en `notes`, nunca inventados en
  `answer_text`.

- **Tachados, ambos casos.** v2 solo cubría "tacha y reescribe". v3 amplía: no
  transcribir nunca lo tachado; si reescribe, quedarse con lo reescrito; si tacha
  sin reescribir, omitirlo; y ante ambigüedad, transcribir la mejor lectura de lo
  válido y anotarlo en `notes` (en vez de inventar).

Se mantiene la ausencia de `format`. En
cambio, se **retira la directiva `/no_think` del prompt**: como se comprobó en v2,
no es ella la que desactiva el razonamiento (lo hace `think=False` en
`OllamaVLMProvider`), así que aportaba ruido sin efecto real. **Pendiente de
revalidar** empíricamente contra `examen_prueba.jpeg` con el test de integración
(ver abajo); anotar aquí el resultado tras ejecutarlo.

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

---

# Fase de corrección

La fase de corrección (`app/pipeline/grading.py`) recibe la transcripción del
alumno más el material del profesor (rúbrica, contexto, examen modelo,
indicaciones) y pide a un **LLM textual** una rúbrica rellenada con calificación
propuesta por ítem y un informe de feedback. El modelo de referencia durante el
desarrollo ha sido un qwen3 textual servido por Ollama en local.

El prompt final vive como constante `GRADING_PROMPT` en `grading.py` (única
fuente de verdad; aquí se explica el porqué, no se duplica).

## v1 — Una sola llamada + validación blanda (versión adoptada)

### Decisiones de diseño

- **Una sola llamada al LLM.** El modelo lee la rúbrica (texto libre) y rellena
  sus ítems en la misma pasada. Se descartó un paso previo de "estructurar la
  rúbrica" por simplicidad para el MVP.
- **Rúbrica de texto libre.** La redacta el profesor: formato libre, pero con
  puntuación por ítem e incluso por nivel ("Mal 0 p / Regular 0,5 p / Bien 1 p").
  Como no hay una lista canónica de ítems de partida, el prompt insiste en usar
  EXACTAMENTE los ítems de la rúbrica (ni inventar ni omitir).
- **Orden de las entradas en el prompt:** rúbrica → contexto → examen modelo →
  indicaciones del profesor → transcripción del alumno. Contexto e indicaciones
  son opcionales (se omiten si no se aportan).
- **El examen modelo es referencia, no verdad absoluta:** el prompt pide criterio
  para puntuar bien respuestas correctas que se desvíen del modelo.
- **`feedback_report` dirigido al profesor** (coherente con el rol orientativo:
  la decisión final es suya).
- **Sin `format` nativo, igual que en transcripción.** Se pide el JSON en el
  prompt + `/no_think` y se parsea con el parser robusto compartido
  (`app/pipeline/utils.py::parse_json_object`, extraído de la fase de
  transcripción para reutilizarlo).
- **`num_ctx` generoso.** El prompt es largo (rúbrica + contexto + examen modelo
  + transcripción), así que el `OllamaLLMProvider` se construye con `num_ctx`
  amplio (p. ej. 16384) en el script y la integración.

### Validación de la salida (blanda)

Tras parsear y validar con Pydantic (`GradingResult`), `_enforce_constraints`
aplica solo lo que **se puede comprobar de forma fiable**:

1. Cada `assigned_score` se recorta al rango `[0, max_score del ítem]` (log
   WARNING si se recorta).
2. `total_score` se **recalcula** como la suma de los `assigned_score` recortados
   y se trunca a `[0, max_score del examen]` (log WARNING si se trunca). Esto
   garantiza el criterio de aceptación de que la nota total esté en rango, sin
   depender de que el modelo sume bien.
3. Detección **blanda** de alucinaciones: para cada `item_name` se comprueba con
   un matching tolerante (normalizado, sin acentos) si aparece en la rúbrica; si
   no, se registra un WARNING. **No falla**: con rúbrica de texto libre la
   comprobación es orientativa, no una verdad rígida.

Si la salida no parsea/valida, `grade_exam` reintenta (`max_retries`, por defecto
2) y, agotados los intentos, lanza `GradingError`.

### Riesgo residual

Los modelos de razonamiento textuales (qwen3) pueden volcar todo al campo
`thinking` y devolver `content` vacío (mismo fenómeno visto en el VLM). El
parseo robusto + reintentos lo mitigan. A diferencia del VLM, el
`OllamaLLMProvider` no expone aún un parámetro `think`; queda anotado como punto
de ajuste si en uso real aparecen muchos intentos vacíos.

### Validación empírica

La v1 se ha validado de extremo a extremo con `scripts/grade_exam.py`: transcripción
(qwen3-vl) + corrección (qwen3:14b) sobre el examen real `examen_prueba.jpeg`
("Fundamentos de redes", 10 p) con la rúbrica, contexto, examen modelo e indicaciones
de `scripts/pipeline_poc/` (todos coherentes con ese examen).

**Resultado (correcto y coherente):**

- Los **7 ítems** de la rúbrica aparecen rellenados, ninguno inventado (criterios 3 y 4).
- `total_score` = **9,25 / 10**, en rango (criterio 2).
- **Cazó el error sembrado a propósito:** el alumno escribió "4 millones" de direcciones
  IPv4 en vez de ~4.300 millones; el ítem *IPv4* recibió 0,75/1,5 con el comentario
  correcto. Es decir, el prompt + la rúbrica + las indicaciones logran que el modelo
  penalice un error de orden de magnitud en lugar de darlo por bueno.
- El `feedback_report` resume la corrección y justifica el descuento sin inventar hechos
  (criterio 5).
- En la fase previa de transcripción se observó un intento vacío de qwen3-vl que se
  resolvió con el reintento (comportamiento ya documentado arriba), sin afectar a la
  corrección.

Reproducible también con el test de integración
`tests/pipeline/test_grading.py::test_grading_examen_real` (se salta si no hay
Ollama/modelo). Si en futuras iteraciones el comportamiento cambia, anotar aquí la nueva
versión del prompt y sus hallazgos.
