# Korrijo

*Korrijo* es una aplicación web para profesores que les facilita la corrección de exámenes manuscritos en español que estén compuestos por **preguntas de desarrollo** y/o **preguntas de respuesta corta**. SOLO
se aceptan pruebas evaluativas con preguntas "de escribir" de este tipo.

La utilidad de la herramienta es que se le proporcione al profesor una
**corrección automática y orientativa de cada examen que proporcione**. De
esta manera la salida que da el sistema para cada prueba consiste en una **calificación orientativa**, una **rúbrica rellenada** y un **informe con *feedback* general** sobre el proceso de corrección llevado a cabo. Con esta información el profesor debería ser capaz de agilizar la evaluación de esos exámenes.

Para crear una **sesión de corrección** se tiene que proporcionar un **examen modelo** (*gold standard*), una **rúbrica de corrección** y opcionalmente **contexto** que quiera aportar el profesor (apuntes, diapositivas, etc.). En una segunda fase se pueden adjuntar los exámenes que se quiere que *Korrijo* procese y para cada uno de ellos se genera
lo que ya se ha mencionado.

**¡IMPORTANTE!**: Korrijo **NO** pretende sustituir el criterio del profesor. Su objetivo es proporcionarle una guía orientativa de los aciertos y errores del alumno, así como una nota propuesta, para que así la revisión manual sea más ágil y sencilla. 

> Este proyecto es la herramienta que he construido para mi **TFG** de Ingeniería Informática (Universidad de Alicante)

> Versión más reciente de la herramienta: **v1.0.0**

---

## Estructura del repositorio

```
korrijo/
├── frontend/       # Aplicación web Next.js
├── backend/        # API REST (FastAPI, Python)
├── openspec/       # Specs SDD
└── docs/           # Dataset de pruebas + Documentación general 
```

Para poder **ejecutar y probar** la herramienta hay que llevar a cabo 3 pasos:

1. Poner en marcha la infraestructura general (A)
2. Arrancar el backend (B)
3. Arrancar el frontend (C)

Se explica todo detalladamente en los siguientes 3 apartados.

---

## A. Servicios necesarios

Se necesita tener levantada una base de datos **PostgreSQL** y el servicio **Mailpit** (servidor de correo).
Ambos se gestiona con Docker Compose. Se necesita tener por tanto el [Docker Engine](https://www.docker.com/products/docker-desktop/) instalado.

Copia el fichero de variables de entorno de la raíz a un .env en el mismo directorio y ajusta los valores si lo consideras adecuado:

```bash
cp .env.example .env
```

Tienes estos comandos disponibles:

| Comando | Efecto |
|---|---|
| `docker compose up -d` | Levanta los servicios necesarios en segundo plano |
| `docker compose down` | Para y elimina los contenedores (los datos persisten) |
| `docker compose down -v` | Para los contenedores y **borra también los volúmenes** (se pierden los datos) |

Al levantarlos los servicios que tendrás disponibles son estos:

| Servicio | Puerto | Descripción |
|---|---|---|
| PostgreSQL | `5432` | Base de datos relacional |
| Mailpit (SMTP) | `1025` | Servidor de correo |
| Mailpit (UI) | `8025` | Interfaz web: http://localhost:8025 |

---

Además, necesitas tener instalado [Ollama](https://ollama.com/download), que es el proveedor de inferencia soportado por ahora, y descargados los modelos abiertos que vayas a usar: uno de visión (OCR) y uno textual.
A mí, con una **NVIDIA RTX 3060** de **12 GB de VRAM** me funcionan bien estos:

- **qwen2.5vl:7b** como modelo de visión. Se encarga de las transcripciones de los exámenes. Súper rápido y bueno para OCR manuscrito en español.

- **qwen3:8b** como modelo textual, que se encarga, principalmente, de corregir los exámenes.

## B. Backend

Tras instalar los elementos que se han mencionado y levantar la infraestructura del sistema, ahora tienes que ejecutar el proyecto *backend*, el cual es un servidor de API REST.

Consulta [`backend/README.md`](./backend/README.md) para entender todo lo relacionado con la parte backend, incluido
como ejecutarlo.

---

## C. Frontend

Por último, necesitas ejecutar la aplicación web *frontend* y podrás acceder
a Korrijo desde [http://localhost:3000](http://localhost:3000). Ten en cuenta que necesitas tener *Node* instalado.

Consulta [`frontend/README.md`](./frontend/README.md) para para entender todo lo relacionado con la parte frontend, incluido
como ejecutarlo para poder probar el sistema.
