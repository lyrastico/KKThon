from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_analysis_finding_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.analysis_finding import AnalysisFindingRepository
from app.schemas.analysis_finding import AnalysisFindingCreate, AnalysisFindingRead, AnalysisFindingUpdate

router = APIRouter(prefix="/analysis-findings", tags=["analysis-findings"])


@router.get("/", response_model=list[AnalysisFindingRead])
async def list_analysis_findings(
    analysis_run_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: AnalysisFindingRepository = Depends(get_analysis_finding_repo),
    current_user=Depends(get_current_user),
):
    if analysis_run_id:
        return await repo.list_by_analysis_run(db, analysis_run_id)
    return await repo.list(db)


@router.post("/", response_model=AnalysisFindingRead)
async def create_analysis_finding(
    payload: AnalysisFindingCreate,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisFindingRepository = Depends(get_analysis_finding_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{finding_id}", response_model=AnalysisFindingRead)
async def get_analysis_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisFindingRepository = Depends(get_analysis_finding_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, finding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis finding not found")
    return item


@router.patch("/{finding_id}", response_model=AnalysisFindingRead)
async def update_analysis_finding(
    finding_id: UUID,
    payload: AnalysisFindingUpdate,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisFindingRepository = Depends(get_analysis_finding_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, finding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis finding not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{finding_id}")
async def delete_analysis_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisFindingRepository = Depends(get_analysis_finding_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, finding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis finding not found")
    await repo.delete(db, item)
    return {"message": "Analysis finding deleted"}
