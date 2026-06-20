from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

NameStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=75)]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None


class UserUpdate(BaseModel):
    name: NameStr | None = None


class AccountDeleteRequest(BaseModel):
    # El cliente debe enviar esta palabra exacta para confirmar el borrado.
    confirm: str
