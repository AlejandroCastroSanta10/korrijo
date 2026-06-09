# Backend de Korrijo 

Se trata de una API hecha en FastAPI, la cual tiene detrás toda la lógica de negocio de Korrijo, así como la interacción
con los modelos de IA.

## Requisitos y dependencias

- Python 3.12+ y el módulo para poder crear entornos virtuales (venv).
- Ollama corriendo (proveedor de inferencia) y tener descargados los modelos que se quiera usar (los que he usado yo 
están en el .env.example).

Para la descarga de dependencias necesarioas, desde este directorio `backend/`:

```bash
# 1. Creamos el entorno virtual
python3 -m venv .venv

# 2. Lo activamos
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\Activate.ps1     # Windows PowerShell

# 3. Actualizamos pip (recomendado)
pip install --upgrade pip

# 4. Instalamos dependencias con pip
pip install -r requirements-dev.txt
```

## Configuración de las variables de entorno

Es **obligatorio** crear un fichero `.env` en backend/ y rellenarlo con los valores adecuados.

Se tiene que copiar la plantilla y ajustar los valores que vienen por defecto si se cree necesario:

```bash
cp .env.example .env
```

## Cuestiones relacionadas con la Base de Datos

Se necesita que el backend tenga acceso a la base de datos PostgreSQL. Para ello los servicios de Docker 
deben estar corriendo (se hace con `docker compose up -d` desde la raíz del proyecto).

Para aplicar las migraciones de la BD, desde el directorio `backend/` con el entorno virtual activado:

```bash
alembic upgrade head
```

Si se quisiera crear una migración a partir de a cambios realizados a los modelos:

```bash
alembic revision --autogenerate -m "descripción"
```

## Endpoints

Se pondrá el listado definitivo de endpoints que configuran la API en versiones posteriores.

## Arrancar el backend

Con el entorno virtual activado:

```bash
uvicorn app.main:app --reload
```

El servidor que expone la API se levantará en [http://localhost:8000](http://localhost:8000).


## Pipeline standalone (probar la funcionalidad principal sin frontend)

La funcionalidad principal de Korrijo (corregir exámenes manuscritos) se puede
probar desde CLI, sin frontend ni base de datos, ni nada, con el script `app/pipeline/run.py`.

Reproduce el flujo de una **sesión de corrección**: el material del profesor
(rúbrica, examen modelo y contexto) se extrae **una sola vez** y se reutiliza
para corregir una **tanda de hasta 3 exámenes**. Por cada examen ejecuta
transcripción (VLM) → corrección (LLM) y produce la rúbrica
rellenada, una nota propuesta y un informe de feedback y métricas de ejecución
(todo ello en un fichero JSON de salida).

> El examen del alumno tiene que ser **PDF escaneado o imagen** (`.jpg`, `.jpeg`,
> `.png`). La rúbrica, el examen modelo y el contexto deben ser **documentos
> nativos** (`.pdf` nativo, `.xlsx`, `.txt`, `.md`, `.csv`): no se admiten PDFs
> escaneados para estos.

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

> **Rendimiento:** La corrección de un examen no debe tardar +5 min en el hardware de
referencia (NVIDIA GeForce RTX 3060 de 12GB de VRAM).