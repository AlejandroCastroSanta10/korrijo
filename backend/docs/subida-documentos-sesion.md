# Subida y extracción de documentos iniciales (fase 1)

Decisiones de diseño de los endpoints que aportan el material del profesor a una
sesión de corrección (contexto, examen modelo y rúbrica) antes de empezar a
corregir exámenes. Corresponde a la pantalla "Nueva sesión" del wireframe.

## Flujo y orquestación

- El sistema trabaja en **dos fases**: (1) la sesión recibe el material del
  profesor y se valida; (2) se suben y corrigen los exámenes. Esto cubre la fase 1.
- **Nada se crea hasta pulsar "Crear sesión de corrección"** (el front retiene los
  ficheros en el navegador). El botón dispara, en orden:
  1. `POST /api/sessions` — crea la sesión en estado `draft`.
  2. `POST /api/sessions/{id}/documents` — una vez por fichero.
  3. `POST /api/sessions/{id}/rubric/validate` — confirma y pasa la sesión a `ready`.

## Tipos de documento

| Tipo | Obligatorio | Cardinalidad |
|------|-------------|--------------|
| `context` | No | Varios |
| `model_exam` | Sí | Único por sesión |
| `rubric` | Sí | Único por sesión |

- **Reemplazo:** volver a subir una `rubric` o un `model_exam` sustituye al anterior
  (se borra el previo de BD y de storage). Por eso no hace falta un endpoint de
  borrado: el contexto sobrante se quita en el cliente antes de enviar, y los únicos
  se reemplazan re-subiendo.

## Validación de la subida

- **Extensiones admitidas:** `.pdf, .xlsx, .txt, .md, .csv` (las que soportan los
  extractores del pipeline). Otra extensión → `422`.
- **Tamaño máximo configurable** (`config.py`): 10 MB para `context`, 5 MB para el
  resto. Excedido → `422`.
- **Extracción de texto:** reutiliza `app.pipeline.extractors`. Se extrae *antes* de
  guardar en storage, para no dejar ficheros huérfanos si falla. PDF escaneado o
  formato no procesable → `422`.

## Estructuración de la rúbrica

- La rúbrica es texto libre. Tras extraerla, un **LLM la convierte en una lista de
  ítems** `{name, max_score, description}` para que el profesor la revise/edite.
- Se comprueba que la **suma de `max_score` cuadre con `max_score` de la sesión**
  (tolerancia `0.01`); si no, se devuelve un **aviso** (no se bloquea).
- Tolerancia a fallos: si el LLM no devuelve una estructura válida, la subida **no
  falla** (se devuelve estructura vacía con aviso). Si el proveedor no está
  disponible (Ollama caído, timeout) → `503`.
- El proveedor LLM se inyecta como dependencia (`get_llm_provider`), sobrescribible
  en tests por un doble; los tests no tocan Ollama.

## Validación final y bloqueo

- `POST .../rubric/validate` exige que existan **rúbrica y examen modelo** (`422` si
  falta alguno), guarda la rúbrica estructurada (potencialmente editada) y pone la
  sesión en `ready`.
- La rúbrica definitiva se persiste en `grading_sessions.rubric_structured` (JSONB),
  **solo al validar** (no al subir).
- **Material congelado:** una vez la sesión está `ready`, subir documentos se rechaza
  con `409`. La regla la garantiza el backend, no solo el front.

## Notas de implementación

- Router dividido en `deps.py` (dependencias compartidas), `sessions_common.py`
  (carga/propiedad/serialización), `sessions.py` (CRUD) y `documents.py` (subida +
  validación), para no concentrar demasiado código.
- Nueva migración Alembic para la columna `rubric_structured`.
- `python-multipart` añadido a `requirements.txt` (necesario para `multipart/form-data`).

## Fase 2 (resuelto)

- La corrección ya consume la **rúbrica estructurada validada** (`rubric_structured`),
  serializada a texto, en vez del texto libre del documento. Ver
  [`correccion-examenes.md`](correccion-examenes.md).
