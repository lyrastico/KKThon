from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.schemas.document import DocumentCreate


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self) -> list[Document]:
        result = await self.db.execute(select(Document).order_by(Document.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, payload: DocumentCreate) -> Document:
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata", {})
        item = Document(**data)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item
