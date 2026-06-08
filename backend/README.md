# Backend de Korrijo 

Se trata de una API hecha en FastAPI. 

## Requisitos

- Python 3.12+
- `pip` y `venv` (incluidos en Python)

## Instalación

Desde el directorio `backend/`:

```bash
# 1. Crear el entorno virtual
python3 -m venv .venv

# 2. Activarlo
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\Activate.ps1     # Windows PowerShell

# 3. Actualizar pip (recomendado)
pip install --upgrade pip

# 4. Instalar dependencias
pip install -r requirements-dev.txt
```

## Variables de entorno

El backend usa `pydantic-settings` para cargar la configuración desde un fichero `.env`. Crear el `.env` es **obligatorio** porque `DATABASE_URL` no tiene valor por defecto.

Copiar la plantilla y ajustar los valores si es necesario:

```bash
cp .env.example .env
```

## Arrancar el servidor

Con el entorno virtual activado:

```bash
uvicorn app.main:app --reload
```

El servidor se levantará en [http://localhost:8000](http://localhost:8000).

### Endpoints

Por ahora son solo estos dos:

- [http://localhost:8000/health](http://localhost:8000/health) — health check, devuelve `{"status": "ok"}`
- [http://localhost:8000/docs](http://localhost:8000/docs) — documentación de la API con Swagger

## Base de datos

> Pre-requisito: los servicios de Docker deben estar corriendo (`docker compose up -d` desde la raíz).

Las migraciones se gestionan con Alembic. Desde el directorio `backend/` con el entorno virtual activado:

```bash
# Aplicar todas las migraciones pendientes
alembic upgrade head

# Crear una nueva migración a partir de los cambios en los modelos
alembic revision --autogenerate -m "descripción"
```

## Pipeline standalone (usar funcionalidad principal sin frontend)

La funcionalidad principal de Korrijo —corregir exámenes manuscritos— se puede
probar de extremo a extremo desde la línea de comandos, sin frontend ni base de
datos, con el script `app/pipeline/run.py`.

Reproduce el flujo de una **sesión de corrección**: el material del profesor
(rúbrica, examen modelo y contexto) se extrae **una sola vez** y se reutiliza
para corregir una **tanda de hasta 3 exámenes**. Por cada examen ejecuta
extracción → transcripción (VLM) → corrección (LLM) y produce la rúbrica
rellenada con nota propuesta, un informe de feedback y métricas de ejecución
(tiempos por fase y VRAM en pico).

### Requisitos

1. **Ollama corriendo** (por defecto en `http://localhost:11434`):

   ```bash
   ollama serve
   ```

2. **Modelos descargados**: uno de visión (VLM) para la transcripción y uno
   textual (LLM) para la corrección. Los del `.env` de ejemplo:

   ```bash
   ollama pull qwen3-vl:latest   # visión
   ollama pull qwen3:14b         # textual
   ```

3. **Modelos configurados en el `.env`** (el script los lee de ahí; no hay flags
   de modelo en el CLI):

   ```bash
   OLLAMA_BASE_URL=http://localhost:11434
   PIPELINE_VLM_MODEL=qwen3-vl:latest
   PIPELINE_LLM_MODEL=qwen3:14b
   ```

> El examen del alumno se sube como **PDF escaneado o imagen** (`.jpg`, `.jpeg`,
> `.png`). La rúbrica, el examen modelo y el contexto deben ser **documentos
> nativos** (`.pdf` nativo, `.xlsx`, `.txt`, `.md`, `.csv`): no se admiten PDFs
> escaneados para esos.

### Ejecución

Desde `backend/`, con el entorno virtual activado:

```bash
# Mínimo: un examen
python -m app.pipeline.run \
    --exam examen.pdf --rubric rubrica.pdf --model-exam modelo.pdf \
    --max-score 10 --output result.json

# Tanda de varios exámenes (mismo material) + contexto e indicaciones
python -m app.pipeline.run \
    --exam alumno1.pdf --exam alumno2.pdf --exam alumno3.pdf \
    --rubric rubrica.pdf --model-exam modelo.pdf \
    --context apuntes.pdf --context temario.md \
    --instructions indicaciones.txt \
    --max-score 10 \
    --output result.json --verbose
```

Argumentos:

- **Obligatorios:** `--exam` (repetible, hasta 3), `--rubric`, `--model-exam`,
  `--max-score` (> 0).
- **Opcionales:** `--context` (repetible), `--instructions` (texto literal o
  ruta a un fichero), `--output` (guarda el resultado completo en JSON),
  `--verbose` (logging DEBUG con tiempos detallados).

La consola imprime, por cada examen, la nota orientativa, la rúbrica rellenada y
los tiempos; al final, un resumen de la tanda (corregidos, aprobados/suspensos,
nota media y tiempo total). Con `--output` se guarda además el resultado completo
(transcripción, corrección y metadatos) en JSON.

Un examen que falle **no aborta la tanda**: se marca con su error y el resto se
sigue corrigiendo. Si falla la preparación de la sesión (p. ej. una rúbrica
ilegible) o no se puede corregir ningún examen, el script termina con código de
salida distinto de 0.

> **Rendimiento:** la transcripción (VLM) es lenta. En una RTX 3060 de 12 GB, un
> examen de tamaño normal se corrige en menos de 5 minutos. La VRAM en pico que
> reporta el script viene de `nvidia-smi` (si no hay GPU NVIDIA, ese dato sale
> vacío).

## Desarrollo

### Linting y formateo

El proyecto usa [Ruff](https://docs.astral.sh/ruff/) para linting y formateo. Es recomendable usar estos comandos de vez en cuando:

```bash
ruff check .           # lint
ruff check --fix .     # lint y corrige automáticamente lo que puede
ruff format .          # formatea
```

### Nuevos routers

¡IMPORTANTE! Los nuevos routers se crean en `app/api/` como módulos separados y se registran en `app/main.py` mediante `app.include_router(...)`.