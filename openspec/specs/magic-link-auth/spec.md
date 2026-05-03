## ADDED Requirements

### Requirement: Solicitar magic link
El sistema SHALL aceptar una petición con un email y responder siempre con 202 Accepted, independientemente de si el email existe en la base de datos. SHALL generar un token criptográficamente seguro (`secrets.token_urlsafe(32)`), persistirlo en `magic_link_tokens` con una expiración configurable, y enviar un email con el enlace al destinatario.

#### Scenario: Solicitud con email válido existente
- **WHEN** se envía `POST /auth/request-magic-link` con `{"email": "docente@ejemplo.com"}` y ese email existe en `users`
- **THEN** el sistema responde 202 Accepted con un mensaje genérico
- **THEN** se crea un registro en `magic_link_tokens` con el email, token y `expires_at` correctos
- **THEN** Mailpit recibe un email a `docente@ejemplo.com` con un enlace de la forma `{app_base_url}/auth/verify?token=...`

#### Scenario: Solicitud con email no registrado
- **WHEN** se envía `POST /auth/request-magic-link` con un email que no existe en `users`
- **THEN** el sistema responde 202 Accepted con el mismo mensaje genérico que para un email existente
- **THEN** se crea igualmente un registro en `magic_link_tokens`

#### Scenario: Solicitud sin campo email
- **WHEN** se envía `POST /auth/request-magic-link` sin el campo `email` en el body
- **THEN** el sistema responde 422 Unprocessable Entity

#### Scenario: Solicitud con formato de email inválido
- **WHEN** se envía `POST /auth/request-magic-link` con `{"email": "no-es-un-email"}`
- **THEN** el sistema responde 422 Unprocessable Entity

---

### Requirement: Rate limiting de solicitudes
El sistema SHALL limitar a 3 solicitudes por email en los últimos `magic_link_expiration_minutes` minutos. Si se supera ese límite SHALL responder 429 Too Many Requests.

#### Scenario: Tercera solicitud permitida
- **WHEN** se han enviado 2 solicitudes previas para el mismo email dentro del período de expiración
- **THEN** una tercera solicitud responde 202 Accepted

#### Scenario: Cuarta solicitud bloqueada
- **WHEN** se han enviado 3 solicitudes previas para el mismo email dentro del período de expiración
- **THEN** una cuarta solicitud responde 429 Too Many Requests

---

### Requirement: Token de magic link de un solo uso
El sistema SHALL rechazar un token que ya haya sido utilizado. Al verificarse correctamente, el token SHALL marcarse con `used_at = now()` y no podrá volver a usarse.

#### Scenario: Token usado por segunda vez
- **WHEN** se envía `POST /auth/verify` con un token que ya tiene `used_at` establecido
- **THEN** el sistema responde 400 con código de error `already_used`

---

### Requirement: Expiración del token
El sistema SHALL rechazar un token cuya `expires_at` sea anterior al momento de la verificación.

#### Scenario: Token expirado
- **WHEN** se envía `POST /auth/verify` con un token cuya `expires_at` es una fecha pasada
- **THEN** el sistema responde 400 con código de error `expired`

---

### Requirement: Contenido del email de magic link
El email SHALL incluir el enlace clicable del magic link, la duración de validez del enlace en minutos, y un aviso de "si no fuiste tú, ignora este mensaje". SHALL enviarse en formato HTML y texto plano.

#### Scenario: Email recibido en Mailpit
- **WHEN** se procesa una solicitud de magic link válida
- **THEN** Mailpit muestra el email con un enlace de la forma `{app_base_url}/auth/verify?token=...` clicable
- **THEN** el email incluye la mención de expiración y el aviso de "si no fuiste tú"

---

### Requirement: Verificar magic link y emitir sesión
El sistema SHALL aceptar un token vía `POST /auth/verify`, validarlo, recuperar o crear el usuario asociado al email del token, y emitir una cookie de sesión firmada.

#### Scenario: Verificación con token válido, usuario existente
- **WHEN** se envía `POST /auth/verify` con un token válido, no expirado y no usado, y el email ya existe en `users`
- **THEN** el sistema responde 200 con los datos del usuario (`id`, `email`, `name`)
- **THEN** la respuesta incluye `Set-Cookie` con la cookie de sesión firmada (HttpOnly, SameSite=Lax)
- **THEN** el token queda marcado con `used_at`

#### Scenario: Verificación con token válido, usuario nuevo
- **WHEN** se envía `POST /auth/verify` con un token válido y el email no existe en `users`
- **THEN** el sistema crea el usuario con ese email
- **THEN** responde 200 con los datos del usuario recién creado
- **THEN** emite la cookie de sesión

#### Scenario: Token inválido (no existe)
- **WHEN** se envía `POST /auth/verify` con un token que no existe en `magic_link_tokens`
- **THEN** el sistema responde 400 con código de error `invalid`

---

### Requirement: Consultar usuario autenticado
El sistema SHALL exponer `GET /auth/me` que devuelve los datos del usuario autenticado leyendo su cookie de sesión.

#### Scenario: Petición autenticada
- **WHEN** se envía `GET /auth/me` con una cookie de sesión válida
- **THEN** el sistema responde 200 con `{"id": "...", "email": "...", "name": "..."}`

#### Scenario: Petición sin cookie
- **WHEN** se envía `GET /auth/me` sin cookie de sesión
- **THEN** el sistema responde 401 Unauthorized

#### Scenario: Petición con cookie manipulada
- **WHEN** se envía `GET /auth/me` con una cookie cuya firma no es válida
- **THEN** el sistema responde 401 Unauthorized

---

### Requirement: Cerrar sesión
El sistema SHALL exponer `POST /auth/logout` que invalida la cookie de sesión del cliente.

#### Scenario: Logout con sesión activa
- **WHEN** se envía `POST /auth/logout` con una cookie de sesión válida
- **THEN** el sistema responde 204 No Content
- **THEN** la respuesta incluye `Set-Cookie` con la cookie de sesión con fecha de expiración pasada

#### Scenario: Logout sin sesión
- **WHEN** se envía `POST /auth/logout` sin cookie de sesión
- **THEN** el sistema responde 204 No Content
