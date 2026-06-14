from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None


class UserUpdate(BaseModel):
    name: NameStr


class AccountDeleteRequest(BaseModel):
    # El cliente debe enviar esta palabra exacta para confirmar el borrado.
    confirm: str
