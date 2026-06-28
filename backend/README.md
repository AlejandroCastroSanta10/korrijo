# Backend de Korrijo 

Se trata de una API hecha en FastAPI, la cual tiene detrás toda la lógica de negocio de Korrijo, así como la interacción
con los modelos de IA abiertos.

## Requisitos y dependencias

- **Python 3.12+** y el módulo para poder crear entornos virtuales (venv).
- **Servidor Ollama** corriendo (proveedor de inferencia) y tener descargados los modelos que se quiera usar (los que he usado yo 
están en /backend/.env.example).

Para la descarga de dependencias necesarias, desde este directorio `backend/`:

```bash
# 1. Creamos el entorno virtual
python3 -m venv .venv
# python -m venv .venv  en Windows

# 2. Lo activamos
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\Activate.ps1     en Windows (PowerShell)

# 3. Actualizamos pip (recomendado)
pip install --upgrade pip

# 4. Instalamos dependencias con pip
pip install -r requirements-dev.txt
```

## Configuración de las variables de entorno del backend

Es **obligatorio** crear un fichero `.env` en backend/ y rellenarlo con los valores adecuados.

Se tiene que copiar la plantilla y ajustar los valores que vienen por defecto si se cree necesario:

```bash
cp .env.example .env
```

## Cuestiones relacionadas con la Base de Datos

Ya se debe tener la BD corriendo en un contendor de Docker.

Para aplicar las migraciones de la BD, desde el directorio `backend/` con el entorno virtual activado:

```bash
alembic upgrade head
```

## Arrancar el backend

Ya puedes arracancar la API REST. Con el entorno virtual activado:

```bash
uvicorn app.main:app --reload
```

El servidor que expone la API se levantará en [http://localhost:8000](http://localhost:8000). En [http://localhost:8000/docs](http://localhost:8000/docs)
puedes ver el listado de endpoints que hay disponibles.

## Explicación del backend

El código vive en `app/` y está organizado por **capas**, de modo que cada una se
ocupa de una cosa y se apoya en la de debajo:

- **`api/`** — Los *endpoints* de la API REST (FastAPI), agrupados por recurso:
  `auth` (login con *magic link*), `users`, `sessions`, `documents`, `exams`,
  `contact` y `health`. Aquí solo se valida la petición y se delega; la lógica
  de verdad está en los servicios. En `deps.py` están las dependencias comunes de muchos de ellos,
  como obtener el usuario autenticado a partir de la cookie de sesión.
- **`services/`** — La lógica de negocio: gestión de sesiones de corrección,
  validación y guardado de los documentos del profesor, corrección de los
  exámenes del alumno, envío de correos (el *magic link* y el formulario de
  contacto), generación de los PDF de salida (rúbrica rellenada e informe) y el
  almacenamiento de ficheros (`storage/`, actualmente en disco local pero detrás de una
  interfaz por si en el futuro se cambia a otro sitio).
- **`pipeline/`** — Todo lo que tiene que ver con la IA, que es el núcleo del
  producto. Está pensado en torno a las **dos fases** de una sesión:
  1. *Preparar la sesión* (una sola vez): el material del profesor —rúbrica,
     examen modelo y contexto— se **extrae a texto** con los `extractors/`
     (PDF nativo, TXT, MD, CSV, XLSX) y la rúbrica se **estructura** a datos con
     el LLM textual.
  2. *Corregir cada examen* (una vez por examen subido): el examen manuscrito se
     **transcribe** con el modelo de visión (VLM, que hace OCR página a página)
     y después el LLM textual lo **corrige** contra el examen modelo y la
     rúbrica, produciendo la nota propuesta y el informe de *feedback*.
  Los proveedores de inferencia (`llm/` y `vlm/`) están detrás de una interfaz
  común y la implementación actual habla con **Ollama**. El `orchestrator.py`
  encadena estas fases y es lo que invocan los servicios.
- **`db/`** — La capa de persistencia con SQLAlchemy: la conexión (`session.py`)
  y los modelos (`models/`): usuario, token del *magic link*, sesión de
  corrección, documentos de la sesión, examen y resultado de corrección. Las
  migraciones se llevan con Alembic (carpeta `alembic/`).
- **`schemas/`** — Los modelos Pydantic que definen la forma de los datos que
  entran y salen por la API (separados de los modelos de base de datos).
- **`core/`** — Configuración central (`config.py`), donde se cargan todas las
  variables de entorno del `.env` (BD, SMTP, modelos, límites de subida, etc.).

Una nota sobre el flujo: corregir un examen tarda un poco (interviene la IA),
así que cuando se sube un examen la corrección se lanza **en segundo plano** y el
examen va pasando por sus estados (esperando, procesando, corregido o error)
hasta que termina. El frontend va consultando ese estado.
