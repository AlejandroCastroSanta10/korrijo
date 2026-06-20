import time

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.services.email import SmtpEmailService

router = APIRouter(tags=["contact"])

_email_service = SmtpEmailService()

# Rate limiting en memoria por IP. 
_recent_by_ip: dict[str, list[float]] = {}


def _check_rate_limit(ip: str) -> None:
    window = settings.contact_rate_limit_window_minutes * 60
    now = time.monotonic()
    recent = [t for t in _recent_by_ip.get(ip, []) if now - t < window]
    if len(recent) >= settings.contact_rate_limit_max:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    recent.append(now)
    _recent_by_ip[ip] = recent


class ContactMessageBody(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    last_name: str | None = Field(default=None, max_length=120)
    email: EmailStr = Field(max_length=254)
    subject: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=2000)


@router.post("/contact", status_code=status.HTTP_202_ACCEPTED)
async def send_contact_message(body: ContactMessageBody, request: Request) -> dict:
    _check_rate_limit(request.client.host if request.client else "unknown")

    full_name = f"{body.name} {body.last_name}".strip() if body.last_name else body.name
    await _email_service.send_contact_message(
        to_email=settings.contact_recipient_email,
        name=full_name,
        from_email=body.email,
        subject=body.subject,
        message=body.message,
    )
    return {"message": "Mensaje enviado correctamente."}
