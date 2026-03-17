from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document_file import DocumentFile
from app.repositories.base import BaseRepository


class DocumentFileRepository(BaseRepository[DocumentFile]):
    def __init__(self):
        super().__init__(DocumentFile)

    async def list_by_document(self, db: AsyncSession, document_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(DocumentFile)
            .where(DocumentFile.document_id == document_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
