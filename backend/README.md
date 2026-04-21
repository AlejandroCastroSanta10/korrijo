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

El backend usa `pydantic-settings` para cargar la configuración. Sus valores se sobreescriben si están declarados en un fichero `.env`.

En `.env.example` hay una plantilla. Para desarrollo local, los valores por defecto definidos en `app/core/config.py` son suficientes, así que crear el `.env` es opcional. Esto es más de cara a producción.

Pero para personalizar algún valor, copiar la plantilla y editarla:

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