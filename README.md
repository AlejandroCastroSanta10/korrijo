# Korrijo

Korrijo es una herramienta web para docentes que automatiza la corrección de exámenes manuscritos. A partir de una rúbrica y un examen modelo, genera un informe de feedback y una calificación propuesta para cada examen subido, reduciendo el tiempo que el profesor dedica a la parte más mecánica de la evaluación.

> **Trabajo de Fin de Grado** — Ingeniería Informática, especialidad Ingeniería del Software.
> Autor: Alejandro Castro Santa. Versión actual: **v0.1.0**

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

## Requisitos previos

- [Node.js](https://nodejs.org/) 20+
- [Python](https://www.python.org/) 3.12+
- [Git](https://git-scm.com/)

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
