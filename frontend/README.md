# Frontend de Korrijo

Aplicación *frontend* de *Korrijo*: la interfaz web con la que el profesor trabaja.
Está construida con [Next.js](https://nextjs.org) (App Router), React y TypeScript,
y habla con la API del backend para todo lo demás.

## Requisitos y dependencias

- **Node.js 20+** y npm.
- El **backend corriendo** (por defecto en `http://localhost:8000`), ya que el
  frontend no tiene lógica propia de negocio: todo lo importante lo pide a la API.

Para instalar las dependencias, desde este directorio `frontend/`:

```bash
npm install
```

## Variables de entorno

Es necesario crear un .env.local también en este directorio.

Copiar `.env.example` y ajustar los valores según el entorno en el que se trabaje:

```bash
cp .env.example .env.local
```

| Variable              | Descripción                        | Valor por defecto          |
| --------------------- | ---------------------------------- | -------------------------- |
| `NEXT_PUBLIC_API_URL` | URL base de la API del backend     | `http://localhost:8000`    |


## Arrancar el frontend

Tienes que ejecutar:

```bash
npm run dev
```

Y al abrir [http://localhost:3000](http://localhost:3000) en el navegador, si has seguido todos los pasos anteriores (infraestructura,
backend y frontend) ya podrás usar *Korrijo*.


## Explicación del frontend

El código vive en `src/` y sigue las convenciones del **App Router** de Next.js.
Las piezas principales son:

- **`app/`** — Las rutas de la aplicación. Están separadas en dos grupos según si
  son públicas o requieren estar autenticado:
  - **`(public)/`** — La parte abierta: la *landing* con el *login* (que funciona
    con *magic link*), la verificación del enlace recibido por correo
    (`auth/verify`) y las páginas de contacto, información del creador y términos.
  - **`(app)/`** — La parte privada, que es la funcionalidad principal. Aquí está
    `new` (fase 1: crear la sesión y subir el material del profesor),
    `session/[id]` (fase 2: subir y corregir exámenes y ver el cuadro de mandos),
    `history` (historial de sesiones) y `settings` (configuración de la cuenta).
  Cada grupo tiene su propio *layout* (cabecera y pie distintos según la zona) y
  en la raíz están el *layout* general y los `providers`.
- **`middleware.ts`** — Protege la parte privada: si se intenta entrar en
  `/app/*` sin la cookie de sesión, redirige al *login*.
- **`components/`** — Los componentes de la interfaz, organizados por uso:
  `ui/` (los primitivos de shadcn/ui), `layout/` (cabeceras y pies, con variantes
  "smart" que cambian según la página), y los de dominio: `sessions/` (subida de
  documentos, revisión de la rúbrica, lista y resultados de exámenes...),
  `auth/` y `contact/`. Todos estos componentes son de shadcn/ui.
- **`lib/`** — La capa de apoyo. `api.ts` es el cliente que habla con el backend
  (un envoltorio sobre `fetch` que envía siempre la cookie de sesión, maneja los
  errores de la API y sabe descargar los PDF de salida); `config.ts` resuelve la
  URL de la API; `hooks/` son los *hooks* de datos (basados en React Query) para
  autenticación, sesiones y usuario; y `utils.ts` tiene utilidades varias.

Sobre el manejo de datos: las peticiones a la API se gestionan con
**TanStack React Query** (carga, caché y revalidación), los formularios con
**react-hook-form** + **Zod** para la validación, y los avisos al usuario con
*toasts* (sonner). Como la corrección de un examen ocurre en segundo plano en el
backend, la pantalla de la sesión va **consultando el estado** de cada examen
hasta que termina (haciendo *polling*).


Por último, destacar que el estilado se ha llevado a cabo con con **Tailwind CSS**.
