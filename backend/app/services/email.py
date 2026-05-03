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
  <p>Haz clic en el siguiente enlace para iniciar sesión en Korrijo:</p>
  <p><a href="{link}">{link}</a></p>
  <p>Este enlace es válido durante <strong>{expiration_minutes} minutos</strong>.</p>

  <p>Si no has sido tú quien ha solicitado iniciar sesión en Korrijo, ignora este mensaje.</p>
</body>
</html>
"""


class EmailService(ABC):
    @abstractmethod
    async def send_magic_link(
        self, to_email: str, link: str, expiration_minutes: int
    ) -> None: ...


class SmtpEmailService(EmailService):
    async def send_magic_link(
        self, to_email: str, link: str, expiration_minutes: int
    ) -> None:
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
