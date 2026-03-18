from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, item_id: UUID):
        result = await db.execute(select(self.model).where(self.model.id == item_id))
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj_in: dict):
        item = self.model(**obj_in)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def create_from_schema(self, db: AsyncSession, payload):
        return await self.create(db, payload.model_dump())

    async def update(self, db: AsyncSession, db_obj, data: dict):
        for field, value in data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_from_schema(self, db: AsyncSession, db_obj, payload):
        return await self.update(db, db_obj, payload.model_dump(exclude_unset=True))

    async def delete(self, db: AsyncSession, db_obj):
        await db.delete(db_obj)
        await db.commit()
