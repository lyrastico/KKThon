from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analysis_run import AnalysisRun
from app.repositories.base import BaseRepository


class AnalysisRunRepository(BaseRepository[AnalysisRun]):
    def __init__(self):
        super().__init__(AnalysisRun)

    async def list_by_document(self, db: AsyncSession, document_id, skip: int = 0, limit: int = 100):
        result = await db.execute(
            select(AnalysisRun)
            .where(AnalysisRun.document_id == document_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
