## Why

Korrijo necesita autenticación de usuarios. El enfoque passwordless con magic link elimina la fricción de gestionar contraseñas y es suficiente para una herramienta de uso periódico en la que los usuarios son profesores con acceso desde navegador.

## What Changes

- Nuevo modelo `MagicLinkToken` en BD: almacena tokens de un solo uso con expiración.
- Nuevo endpoint `POST /auth/request-magic-link`: genera un token, lo persiste y envía el enlace por email. Devuelve siempre 202 (anti-enumeración). Incluye rate limiting: máximo 3 solicitudes por email en 15 minutos.
- Nueva abstracción `EmailService` con implementación `SmtpEmailService` (aiosmtplib + Mailpit en local).
- Nuevo endpoint `POST /auth/verify`: valida el token, crea el usuario si no existe, y emite una cookie de sesión firmada (itsdangerous).
- Nuevo endpoint `GET /auth/me`: devuelve el usuario autenticado leyendo la cookie de sesión.
- Nuevo endpoint `POST /auth/logout`: invalida la cookie de sesión.
- Nueva dependencia `get_current_user` en `app/api/deps.py` para proteger endpoints futuros.
- Nuevas variables de configuración: SMTP, magic link expiration, app base URL, session secret key, cookie settings.

## Capabilities

### New Capabilities

- `magic-link-auth`: Flujo completo de autenticación passwordless — solicitud de magic link con envío de email y rate limiting, verificación de token con creación de usuario, emisión y gestión de cookie de sesión.

### Modified Capabilities

*(ninguna)*

## Impact

- **API**: nuevas rutas bajo `/auth/` registradas en `app/main.py`
- **Base de datos**: nuevo modelo `MagicLinkToken` + migración Alembic; el modelo `User` existente se usa tal cual
- **Dependencias nuevas**: `aiosmtplib` (envío SMTP async), `itsdangerous` (firma de cookies)
- **Configuración**: nuevas variables obligatorias (`session_secret_key`) y opcionales con defaults para desarrollo (`smtp_host`, `smtp_port`, `smtp_from`, `magic_link_expiration_minutes`, `app_base_url`, `session_cookie_name`, `session_max_age_days`)
- **Infraestructura**: Mailpit ya disponible en el `docker-compose.yml`; no requiere Redis
