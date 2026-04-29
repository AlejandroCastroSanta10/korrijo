# Korrijo - Frontend

Frontend de Korrijo. Construido con [Next.js](https://nextjs.org).

## Variables de entorno

| Variable              | Descripción                        | Valor por defecto          |
| --------------------- | ---------------------------------- | -------------------------- |
| `NEXT_PUBLIC_API_URL` | URL base de la API del backend     | `http://localhost:8000`    |

Copiar `.env.example` a `.env.local` y ajustar los valores según el entorno en el que se trabaje:

```bash
cp .env.example .env.local
```
## Desarrollo

> El backend debe estar corriendo en `localhost:8000` antes de arrancar el frontend, o la llamada a `/health` mostrará un error en pantalla.

```bash
npm run dev
```

Abrir [http://localhost:3000](http://localhost:3000) en el navegador. La página raíz muestra el estado de la conexión con el backend.

## Sistema de diseño

Se usa shadcn/ui. Sus componentes instalados se ubican en `src/components/ui`. Si queremos modificar el estilo de la app habrá que modificar
los ficheros `components.json` y `src/app/globals.css`. Si se desea también se pueden modificar/ampliar los componentes shadcn instalados.
