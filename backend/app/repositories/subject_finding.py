from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subject_finding import SubjectFinding
from app.repositories.base import BaseRepository


class SubjectFindingRepository(BaseRepository[SubjectFinding]):
    def __init__(self):
        super().__init__(SubjectFinding)

    async def list_by_run(self, db: AsyncSession, subject_consistency_run_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(SubjectFinding)
            .where(SubjectFinding.subject_consistency_run_id == subject_consistency_run_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
