from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings

_TEXT_TEMPLATE = """\
Hola,

Haz clic en el siguiente enlace para iniciar sesión en Korrijo:

{link}

Este enlace es válido durante {expiration_minutes} minutos.

Si no has sido tú quien ha solicitado iniciar sesión en Korrijo, ignora este mensaje.
"""

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<body>
  <p>Hola,</p>
  <p>Haz clic en el siguiente enlace para iniciar sesión en <i>Korrijo</i>:</p>
  <p><a href="{link}">{link}</a></p>
  <p>Este enlace es válido durante <strong>{expiration_minutes} minutos</strong>.</p>

  <p>Si no has sido tú quien ha solicitado iniciar sesión en <i>Korrijo</i>, ignora este mensaje.</p>
</body>
</html>
"""


_CONTACT_TEMPLATE = """\
Han escrito un nuevo mensaje desde el formulario de contacto de Korrijo.

De: {name}
Email: {email}
Asunto: {subject}

Mensaje:
{message}
"""


class EmailService(ABC):
    @abstractmethod
    async def send_magic_link(self, to_email: str, link: str, expiration_minutes: int) -> None: ...

    @abstractmethod
    async def send_contact_message(
        self, to_email: str, name: str, from_email: str, subject: str, message: str
    ) -> None: ...


class SmtpEmailService(EmailService):
    async def send_magic_link(self, to_email: str, link: str, expiration_minutes: int) -> None:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Tu enlace de acceso a Korrijo"
        message["From"] = settings.smtp_from
        message["To"] = to_email

        message.attach(
            MIMEText(
                _TEXT_TEMPLATE.format(link=link, expiration_minutes=expiration_minutes),
                "plain",
            )
        )
        message.attach(
            MIMEText(
                _HTML_TEMPLATE.format(link=link, expiration_minutes=expiration_minutes),
                "html",
            )
        )

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
        )

    async def send_contact_message(
        self, to_email: str, name: str, from_email: str, subject: str, message: str
    ) -> None:
        email = MIMEText(
            _CONTACT_TEMPLATE.format(
                name=name, email=from_email, subject=subject, message=message
            ),
            "plain",
        )
        email["Subject"] = f"[Contacto Korrijo] {subject}"
        email["From"] = settings.smtp_from
        email["To"] = to_email
        email["Reply-To"] = from_email

        await aiosmtplib.send(
            email,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
        )
