# Subida de exámenes y corrección asíncrona (fase 2)

Decisiones de diseño de los endpoints que reciben los exámenes de los alumnos y
los corrigen. Corresponde a la pantalla "Sesión de corrección" del wireframe.

## Flujo

1. `POST /api/sessions/{id}/exams` — multipart con uno o varios campos `file`
   (hasta `max_exams_per_upload`, 3 por defecto). Crea un `Exam` en `pending` por
   fichero, agenda el pipeline como `BackgroundTask` y responde **202** con la lista
   de exámenes creados. La respuesta es inmediata.
2. El cliente hace **polling**: el estado vive en cada `Exam` (`pending` →
   `processing` → `completed`/`error`). Se consulta con `GET /api/sessions/{id}`
   (ya devuelve la lista de exámenes y los contadores) o, para el resultado
   completo de uno, con `GET /api/sessions/{id}/exams/{exam_id}`.

No hay endpoint de listado propio (`GET .../exams`) ni de borrado por examen: el
detalle de la sesión ya lista los exámenes con su estado, y el borrado es a nivel
de sesión (papelera del historial).

## Descarga de PDFs

Para un examen ya corregido (`completed`):

- `GET /api/sessions/{id}/exams/{exam_id}/rubric.pdf` — rúbrica rellenada (tabla de
  ítems con puntuación asignada/máxima y comentario, total destacado).
- `GET /api/sessions/{id}/exams/{exam_id}/feedback.pdf` — informe (resumen + feedback
  detallado del modelo + disclaimer "calificación orientativa generada por IA").

Decisiones:

- **`reportlab`** (pura-Python, sin dependencias de sistema) en `pdf_generator.py`.
- **Sin caché:** se generan al vuelo desde el `GradingResult` ya persistido (cuestión
  de milisegundos); cachear no compensa a esta escala.
- Examen sin corregir todavía → `409`. Headers: `Content-Type: application/pdf` y
  `Content-Disposition: attachment` con un `filename` que incluye el nombre del examen
  (con `filename*` UTF-8 para nombres no ASCII).
- Rutas anidadas bajo la sesión, por coherencia con el resto del router de exámenes.

## Validación de la subida

- **Formatos:** `.pdf, .jpg, .jpeg, .png` (PDF escaneado o imagen). Otro → `422`.
- **Tamaño máximo** (`max_exam_upload_bytes`). Excedido → `422`.
- **Sesión `ready`:** subir a una sesión en `draft` → `409`. Solo se corrige cuando
  el material está validado y congelado.
- Se validan **todos** los ficheros antes de tocar el storage; uno inválido aborta
  la subida sin dejar ficheros huérfanos. La key incluye el `exam.id` para que dos
  ficheros con el mismo nombre no colisionen.

## Procesamiento en background

- `process_exam(exam_id, session, storage, vlm, llm)` es la función central, con sus
  dependencias inyectadas (testeable sin Ollama). `run_exam_in_background(exam_id)`
  es el envoltorio que agenda el endpoint: abre **su propia sesión de BD** (la de la
  request ya está cerrada cuando el task corre) y construye sus proveedores.
- Pasos: marca `processing` + `started_at` → reconstruye el material de la sesión
  desde lo ya persistido (sin re-extraer) → vuelca el examen del storage a un
  temporal → invoca `correct_exam` (transcripción VLM + corrección LLM) → guarda
  `GradingResult` y marca `completed` + `completed_at`.
- **Material reutilizado:** la `CorrectionSession` se arma con la `rubric_structured`
  validada (serializada a texto), el `extracted_text` del examen modelo y de los
  contextos, y las indicaciones del profesor combinadas. No se vuelve a extraer nada.
- **Errores:** cualquier fallo deja el examen en `error` con un `error_message`
  legible (no traceback). `process_exam` nunca propaga.

## Concurrencia

`BackgroundTasks` de FastAPI ejecuta las tareas **en serie** dentro del worker, así
que dos exámenes de una misma subida no se solapan ni se pisan en la BD. Cada task
usa su propia sesión, así que tampoco comparten estado de SQLAlchemy.

## Inyección de dependencias

- `get_exam_runner` devuelve `run_exam_in_background`; en los tests se sobrescribe
  por un doble que solo registra los `exam_id` agendados, de modo que la subida no
  dispara el pipeline real.
- `process_exam` se prueba aparte, con `FakeVLM`/`FakeLLM` que devuelven JSON válido
  (camino feliz) o lanzan (camino de error). Los tests no tocan Ollama.
