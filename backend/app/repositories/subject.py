from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subject import Subject
from app.schemas.subject import SubjectCreate


class SubjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self) -> list[Subject]:
        result = await self.db.execute(select(Subject).order_by(Subject.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, payload: SubjectCreate) -> Subject:
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata", {})
        item = Subject(**data)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item
