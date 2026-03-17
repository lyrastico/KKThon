from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.schemas.common import ORMModel


class ProfileCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    is_active: bool = True


class ProfileUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None


class ProfileRead(ORMModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
