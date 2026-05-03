## 1. Dependencias y configuración

- [x] 1.1 Añadir `aiosmtplib` e `itsdangerous` a `backend/requirements.txt`
- [x] 1.2 Añadir variables SMTP a `app/core/config.py`: `smtp_host` (default `localhost`), `smtp_port` (default `1025`), `smtp_from` (default `noreply@korrijo.local`)
- [x] 1.3 Añadir variables de magic link a `app/core/config.py`: `magic_link_expiration_minutes` (default `15`), `app_base_url` (default `http://localhost:3000`)
- [x] 1.4 Añadir variables de sesión a `app/core/config.py`: `session_secret_key` (obligatorio, sin default), `session_cookie_name` (default `korrijo_session`), `session_max_age_days` (default `30`)
- [x] 1.5 Actualizar `backend/.env.example` con las nuevas variables

## 2. Modelo MagicLinkToken

- [x] 2.1 Crear `app/db/models/magic_link_token.py` con campos: `id` (UUID, PK, gen_random_uuid()), `token` (String, único, indexado, no nulo), `email` (String, no nulo), `expires_at` (DateTime timezone), `used_at` (DateTime timezone, nullable), `created_at` (DateTime timezone, server_default now())
- [x] 2.2 Exportar `MagicLinkToken` desde `app/db/models/__init__.py`
- [x] 2.3 Generar migración Alembic: `alembic revision --autogenerate -m "create magic_link_tokens table"`
- [x] 2.4 Aplicar migración: `alembic upgrade head`

## 3. Servicio de email

- [x] 3.1 Crear `app/services/email.py` con clase abstracta `EmailService` y método `send_magic_link(to_email: str, link: str, expiration_minutes: int) -> None`
- [x] 3.2 Implementar `SmtpEmailService` en el mismo fichero usando `aiosmtplib` (sin autenticación, compatible con Mailpit)
- [x] 3.3 Añadir plantilla de email en HTML y texto plano: saludo, enlace clicable, mención de expiración en X minutos, aviso "si no fuiste tú, ignora este mensaje"

## 4. Servicio de autenticación — solicitud

- [x] 4.1 Crear `app/services/auth.py` con función `create_magic_link_token(email: str, session: AsyncSession) -> str` que genera el token con `secrets.token_urlsafe(32)`, persiste en BD y devuelve la URL completa del enlace
- [x] 4.2 Implementar `count_recent_tokens(email: str, session: AsyncSession) -> int` que cuenta tokens del mismo email creados en los últimos `magic_link_expiration_minutes` minutos

## 5. Servicio de autenticación — verificación y sesión

- [x] 5.1 Implementar `verify_magic_link_token(token: str, session: AsyncSession) -> User` en `app/services/auth.py`: valida existencia, expiración y uso del token; crea o recupera el usuario; marca `used_at`; lanza excepciones específicas (`TokenInvalid`, `TokenExpired`, `TokenAlreadyUsed`)
- [x] 5.2 Crear `app/services/session.py` con helpers `sign_session(user_id: str) -> str` y `verify_session(cookie_value: str) -> str` usando `itsdangerous.URLSafeTimedSerializer`

## 6. Router y endpoints

- [x] 6.1 Crear `app/api/deps.py` con dependencia `get_current_user(request: Request, session: AsyncSession) -> User` que lee y verifica la cookie de sesión, devuelve el usuario o lanza 401
- [x] 6.2 Crear `app/api/auth.py` con `POST /auth/request-magic-link`: valida body, comprueba rate limit (429 si excedido), llama a `create_magic_link_token`, llama a `SmtpEmailService.send_magic_link`, devuelve 202
- [x] 6.3 Añadir `POST /auth/verify` en el mismo router: valida body, llama a `verify_magic_link_token`, emite cookie HttpOnly + SameSite=Lax (Secure solo si `app_base_url` empieza por `https`), devuelve 200 con datos del usuario
- [x] 6.4 Añadir `GET /auth/me` en el mismo router usando `get_current_user`, devuelve `{"id", "email", "name"}`
- [x] 6.5 Añadir `POST /auth/logout` en el mismo router: elimina la cookie (Set-Cookie con expiración pasada), devuelve 204
- [x] 6.6 Registrar el router en `app/main.py` con prefijo `/auth`
- [x] 6.7 Verificar que el middleware CORS tiene `allow_credentials=True` y que `allow_origins` no es `["*"]`

## 7. Tests

- [x] 7.1 `POST /auth/request-magic-link` con email válido devuelve 202
- [x] 7.2 Tras la solicitud existe un registro en `magic_link_tokens` con token, email y `expires_at` correctos
- [x] 7.3 El servicio de email es invocado (mock de `SmtpEmailService`, no envía de verdad)
- [x] 7.4 La cuarta solicitud para el mismo email en menos de `magic_link_expiration_minutes` minutos devuelve 429
- [x] 7.5 `POST /auth/verify` con token válido devuelve 200, emite cookie de sesión y marca `used_at`
- [x] 7.6 `POST /auth/verify` con token expirado devuelve 400 con código `expired`
- [x] 7.7 `POST /auth/verify` con token ya usado devuelve 400 con código `already_used`
- [x] 7.8 `POST /auth/verify` con token inexistente devuelve 400 con código `invalid`
- [x] 7.9 `GET /auth/me` con cookie de sesión válida devuelve el usuario correcto
- [x] 7.10 `GET /auth/me` sin cookie devuelve 401
- [x] 7.11 `POST /auth/logout` con cookie válida devuelve 204 y la cookie queda invalidada
