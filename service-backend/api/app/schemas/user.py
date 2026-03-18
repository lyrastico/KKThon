from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr | None = None
    fullname: str | None = None


class UserCreate(UserBase):
    """Création explicite (user_id = JWT après inscription)."""
    pass


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    fullname: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    email: str | None
    fullname: str | None
    created_at: datetime
    updated_at: datetime
