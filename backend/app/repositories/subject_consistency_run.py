from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subject_consistency_run import SubjectConsistencyRun
from app.repositories.base import BaseRepository


class SubjectConsistencyRunRepository(BaseRepository[SubjectConsistencyRun]):
    def __init__(self):
        super().__init__(SubjectConsistencyRun)

    async def list_by_subject(self, db: AsyncSession, subject_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(SubjectConsistencyRun)
            .where(SubjectConsistencyRun.subject_id == subject_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
