from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subject import Subject
from app.repositories.base import BaseRepository


class SubjectRepository(BaseRepository[Subject]):
    def __init__(self):
        super().__init__(Subject)

    async def list_by_organization(self, db: AsyncSession, organization_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(Subject)
            .where(Subject.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_from_schema(self, db: AsyncSession, payload):
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata", {})
        return await self.create(db, data)

    async def update_from_schema(self, db: AsyncSession, db_obj, payload):
        data = payload.model_dump(exclude_unset=True)
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        return await self.update(db, db_obj, data)