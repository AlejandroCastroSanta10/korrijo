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