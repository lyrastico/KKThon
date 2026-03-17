from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analysis_finding import AnalysisFinding
from app.repositories.base import BaseRepository


class AnalysisFindingRepository(BaseRepository[AnalysisFinding]):
    def __init__(self):
        super().__init__(AnalysisFinding)

    async def list_by_analysis_run(self, db: AsyncSession, analysis_run_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(AnalysisFinding)
            .where(AnalysisFinding.analysis_run_id == analysis_run_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
