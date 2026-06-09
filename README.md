# Korrijo

Korrijo es una herramienta web para profesores que les facilita la corrección de exámenes manuscritos que estén compuestos por **preguntas de desarrollo** y/o **preguntas de respuesta corta**, pero todas "de escribir". 

Para crear una **sesión de corrección** se tiene que proporcionar un examen modelo (*gold standard*), una rúbrica y opcionalmente contexto que quiera aportar el profesor (apuntes, diapositivas, etc.). En una segunda fase se pueden adjuntar los exámenes que se quieran corregir y para cada uno de ellos se genera una calificación propuesta y un informe de feedback para el profesor.

Korrijo **NO** pretende sustituir el criterio del profesor. Su objetivo es proporcionarle una guía orientativa de los aciertos y errores del alumno, así como una nota propuesta, para que así la corrección manual sea más ágil y sencilla. 

> Este proyecto es la herramienta construida para el **TFG** de Ingeniería Informática (especialidad Ingeniería del Software) de Alejandro Castro Santa.

> Versión actual: **v0.3.0**

---

## Estructura del repositorio

```
korrijo/
├── frontend/       # Aplicación web Next.js
├── backend/        # API REST (FastAPI, Python)
├── openspec/       # Specs SDD
└── docs/           # Documentación general del proyecto
```

Para poder probar la herramienta hay que llevar a cabo 3 cosas:

1. Poner en marcha la infraestructura general (A)
2. Arrancar el backend (B)
3. Arrancar el frontend (C)

Se explica todo detalladamente en los siguientes 3 apartados.

---

## A. Servicios necesarios

Se necesita tener levantada una base de datos PostgreSQL y el servicio Mailpit (servidor de correo).
Ambos se gestiona con Docker Compose. Se necesita tener el Docker Engine instalado, por tanto.

Copia el fichero de variables de entorno a un .env y ajusta los valores si lo consideras adecuado:

```bash
cp .env.example .env
```

Tienes estos comandos disponibles:

| Comando | Efecto |
|---|---|
| `docker compose up -d` | Levanta los servicios en segundo plano |
| `docker compose down` | Para y elimina los contenedores (los datos persisten) |
| `docker compose down -v` | Para los contenedores y **borra también los volúmenes** (se pierden los datos) |

Los servicios disponibles son estos:

| Servicio | Puerto | Descripción |
|---|---|---|
| PostgreSQL | `5432` | Base de datos |
| Mailpit (SMTP) | `1025` | Servidor de correo |
| Mailpit (UI) | `8025` | Interfaz web: http://localhost:8025 |

---

## B. Backend

Consulta [`backend/README.md`](./backend/README.md) para entender todo lo relacionado con la parte backend, incluido
como ejecutarlo.

---

## C. Frontend

Consulta [`frontend/README.md`](./frontend/README.md) para para entender todo lo relacionado con la parte frontend, incluido
como ejecutarlo ya poder probar el sistema.
