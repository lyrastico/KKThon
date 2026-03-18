from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.schemas.common import ORMModel


class OrganizationMemberCreate(BaseModel):
    organization_id: UUID
    user_id: UUID
    role: str
    invited_by: UUID | None = None


class OrganizationMemberUpdate(BaseModel):
    role: str | None = None
    invited_by: UUID | None = None


class OrganizationMemberRead(ORMModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    invited_by: UUID | None
    created_at: datetime
