from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class OrganizationCreate(BaseModel):
    name: str
    slug: str
    is_active: bool = True


class OrganizationRead(ORMModel):
    id: UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
