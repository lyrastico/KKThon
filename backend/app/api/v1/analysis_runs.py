from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_analysis_finding_repo, get_analysis_run_repo, get_document_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.analysis_finding import AnalysisFindingRepository
from app.repositories.analysis_run import AnalysisRunRepository
from app.repositories.document import DocumentRepository
from app.schemas.analysis_run import AnalysisRunCreate, AnalysisRunRead, AnalysisRunUpdate
from app.schemas.silver import SilverIngestResponse, SilverPayload
from app.services.document_analyzer import DocumentAnalyzerService

router = APIRouter(prefix="/analysis-runs", tags=["analysis-runs"])


@router.post("/ingest-silver", response_model=SilverIngestResponse)
async def ingest_silver_analysis(
    payload: SilverPayload,
    db: AsyncSession = Depends(get_db),
    analysis_run_repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    analysis_finding_repo: AnalysisFindingRepository = Depends(get_analysis_finding_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    service = DocumentAnalyzerService(
        analysis_run_repo=analysis_run_repo,
        analysis_finding_repo=analysis_finding_repo,
        document_repo=document_repo,
    )
    return await service.ingest_silver_payload(db, payload)


@router.get("/", response_model=list[AnalysisRunRead])
async def list_analysis_runs(
    document_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    current_user=Depends(get_current_user),
):
    if document_id:
        return await repo.list_by_document(db, document_id)
    return await repo.list(db)


@router.post("/", response_model=AnalysisRunRead)
async def create_analysis_run(
    payload: AnalysisRunCreate,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{analysis_run_id}", response_model=AnalysisRunRead)
async def get_analysis_run(
    analysis_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, analysis_run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return item


@router.patch("/{analysis_run_id}", response_model=AnalysisRunRead)
async def update_analysis_run(
    analysis_run_id: UUID,
    payload: AnalysisRunUpdate,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, analysis_run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{analysis_run_id}")
async def delete_analysis_run(
    analysis_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: AnalysisRunRepository = Depends(get_analysis_run_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, analysis_run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    await repo.delete(db, item)
    return {"message": "Analysis run deleted"}
