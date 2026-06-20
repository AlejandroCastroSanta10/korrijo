from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.services.email import SmtpEmailService

router = APIRouter(tags=["contact"])

_email_service = SmtpEmailService()


class ContactMessageBody(BaseModel):
    name: str = Field(min_length=1)
    last_name: str | None = None
    email: EmailStr
    subject: str = Field(min_length=1)
    message: str = Field(min_length=1)


@router.post("/contact", status_code=status.HTTP_202_ACCEPTED)
async def send_contact_message(body: ContactMessageBody) -> dict:
    full_name = f"{body.name} {body.last_name}".strip() if body.last_name else body.name
    await _email_service.send_contact_message(
        to_email=settings.contact_recipient_email,
        name=full_name,
        from_email=body.email,
        subject=body.subject,
        message=body.message,
    )
    return {"message": "Mensaje enviado correctamente."}
