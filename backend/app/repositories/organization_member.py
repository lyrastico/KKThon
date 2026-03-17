from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.organization_member import OrganizationMember
from app.repositories.base import BaseRepository


class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    def __init__(self):
        super().__init__(OrganizationMember)

    async def list_by_organization(self, db: AsyncSession, organization_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_by_user(self, db: AsyncSession, user_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
