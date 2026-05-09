# Korrijo

Korrijo es una herramienta web para docentes que automatiza la corrección de exámenes manuscritos. A partir de una rúbrica y un examen modelo, genera un informe de feedback y una calificación propuesta para cada examen subido, reduciendo el tiempo que el profesor dedica a la parte más mecánica de la evaluación.

> **Trabajo de Fin de Grado** — Ingeniería Informática, especialidad Ingeniería del Software.
> Autor: Alejandro Castro Santa. Versión actual: **v0.2.0**

---

## Estructura del repositorio

```
korrijo/
├── frontend/       # Aplicación web (Next.js + TypeScript)
├── backend/        # API REST (Python + FastAPI)
├── openspec/       # Specs SDD
└── docs/           # Documentación general del proyecto
```

---

## Requisitos para ejecutar la aplicación en local

- [Node.js](https://nodejs.org/) 20+
- [Python](https://www.python.org/) 3.12+
- [Docker](https://www.docker.com/)

---

## Infraestructura local

La infraestructura de desarrollo (base de datos y servidor de correo) se gestiona con Docker Compose.

Copia el fichero de variables de entorno y ajusta los valores si lo necesitas:

```bash
cp .env.example .env
```

| Comando | Efecto |
|---|---|
| `docker compose up -d` | Levanta los servicios en segundo plano |
| `docker compose down` | Para y elimina los contenedores (los datos persisten) |
| `docker compose down -v` | Para los contenedores y **borra también los volúmenes** (se pierden los datos) |

### Servicios disponibles

| Servicio | Puerto | Descripción |
|---|---|---|
| PostgreSQL | `5432` | Base de datos principal |
| Mailpit (SMTP) | `1025` | Servidor de correo para desarrollo |
| Mailpit (UI) | `8025` | Interfaz web: http://localhost:8025 |

---

## Cómo arrancar el proyecto en local

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd korrijo
```

### 2. Arrancar el backend

```bash
cd backend
```

Consulta [`backend/README.md`](./backend/README.md) para los pasos detallados (entorno virtual, variables de entorno, ejecución del servidor).

### 3. Arrancar el frontend

```bash
cd frontend
```

Consulta [`frontend/README.md`](./frontend/README.md) para los pasos detallados (instalación de dependencias, variables de entorno, servidor de desarrollo).

---

## Estado del proyecto

Korrijo es el TFG de Alejandro Castro Santa, actualmente en desarrollo activo. La idea es conseguir un MVP para la entrega
del trabajo y en el futuro continuar su desarrollo.

---

## Licencia

Código académico desarrollado como Trabajo de Fin de Grado. No se ha definido una licencia de uso pública (al menos para la versión actual).
