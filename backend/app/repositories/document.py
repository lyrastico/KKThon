from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self):
        super().__init__(Document)

    async def list_by_subject(self, db: AsyncSession, subject_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(Document)
            .where(Document.subject_id == subject_id)
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