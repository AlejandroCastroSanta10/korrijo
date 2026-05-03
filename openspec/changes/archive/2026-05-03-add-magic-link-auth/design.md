## Context

El proyecto no tiene autenticación. Se implementa el flujo completo de magic link en dos endpoints: solicitud (`POST /auth/request-magic-link`) y verificación (`POST /auth/verify`), más gestión de sesión (`GET /auth/me`, `POST /auth/logout`). La infraestructura de email (Mailpit) ya está disponible en el docker-compose. El modelo `User` ya existe en BD.

## Goals / Non-Goals

**Goals:**
- Flujo passwordless completo: solicitar enlace → recibir email → verificar token → sesión activa
- Rate limiting sin dependencias externas (sin Redis)
- Abstracción del proveedor de email intercambiable en el futuro
- Anti-enumeración: la respuesta no revela si un email está registrado

**Non-Goals:**
- OAuth / login social
- Autenticación multifactor
- Invalidación activa de sesiones (logout remoto, sesiones concurrentes)
- Refresh tokens

## Decisions

### 1. Rate limiting en BD, sin Redis

**Decisión:** contar los tokens del mismo email creados en los últimos `magic_link_expiration_minutes` minutos directamente en `magic_link_tokens`. Si hay 3 o más, devolver 429.

**Alternativa descartada:** Redis + sliding window counter. Añade una dependencia de infraestructura innecesaria para el volumen de tráfico esperado en v0.1.

**Trade-off:** bajo carga alta, múltiples requests concurrentes pueden pasar el límite antes de que los tokens queden persistidos. Aceptable para v0.1 dado el perfil de uso (profesores individuales).

---

### 2. Token almacenado en claro

**Decisión:** guardar el token en BD sin hashear.

**Alternativa descartada:** hashear con SHA-256 antes de persistir (como se hace con contraseñas).

**Rationale:** los magic link tokens son de un solo uso, corta duración (15 min) y alta entropía (`secrets.token_urlsafe(32)` = 256 bits). El riesgo de exposición en BD es bajo y no justifica la complejidad adicional en v0.1.

---

### 3. Sesión con cookie firmada (itsdangerous), no JWT stateless

**Decisión:** emitir una cookie HttpOnly + SameSite=Lax con un payload firmado por `itsdangerous.URLSafeTimedSerializer`.

**Alternativa descartada:** JWT Bearer token en header `Authorization`.

**Rationale:** el cliente es un navegador; las cookies evitan exponer el token a JavaScript (XSS). `itsdangerous` permite verificar integridad y expiración sin consultar la BD en cada request. El logout elimina la cookie del cliente; no se necesita lista de revocación en v0.1.

**Limitación conocida:** el logout solo invalida la cookie localmente; si alguien copió la cookie antes del logout, seguirá siendo válida hasta que expire (`session_max_age_days`). Aceptable para v0.1.

---

### 4. Abstracción EmailService

**Decisión:** clase abstracta `EmailService` con método `send_magic_link(to_email, link)` e implementación `SmtpEmailService` (aiosmtplib).

**Rationale:** desacopla el transporte del resto de la lógica. En tests se inyecta un mock sin tocar el código de negocio. En el futuro se puede añadir `SendgridEmailService` sin modificar el router ni el servicio de auth.

---

### 5. Creación de usuario en verificación, no en solicitud

**Decisión:** `create_magic_link_token` no comprueba si el email existe en `users`. El usuario se crea (o recupera) en `verify_magic_link_token`, cuando el token ha sido validado.

**Rationale:** evita revelar si un email está registrado durante la fase de solicitud, reforzando la anti-enumeración. La creación lazy de usuario simplifica el flujo de onboarding (el docente no necesita registrarse explícitamente).

---

### 6. Secure flag de la cookie solo en producción

**Decisión:** `Secure=True` solo cuando la configuración no use `localhost` / cuando se detecte entorno de producción. En desarrollo (Mailpit + localhost) se omite para no requerir HTTPS.

**Implementación:** añadir un campo `production` o `debug` a `Settings`, o derivarlo de `app_base_url` si empieza por `https`.

## Risks / Trade-offs

| Riesgo | Mitigación |
|--------|-----------|
| Race condition en rate limiting (requests concurrentes) | Aceptado en v0.1; mitigar con índice y constraint en BD si fuera necesario |
| Cookie robada = sesión válida hasta expiración | Duración de sesión configurable (`session_max_age_days`); en v0.2 se puede añadir invalidación activa |
| Token en claro en BD expuesto si hay SQL injection | Seguir buenas prácticas ORM (consultas parametrizadas con SQLAlchemy); no mitigación específica para el token |
| aiosmtplib sin autenticación en local (Mailpit) | Mailpit acepta SMTP sin auth; en producción se configuran credenciales vía variables de entorno |
