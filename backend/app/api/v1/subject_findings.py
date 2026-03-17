from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_subject_finding_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.subject_finding import SubjectFindingRepository
from app.schemas.subject_finding import SubjectFindingCreate, SubjectFindingRead, SubjectFindingUpdate

router = APIRouter(prefix="/subject-findings", tags=["subject-findings"])


@router.get("/", response_model=list[SubjectFindingRead])
async def list_subject_findings(
    subject_consistency_run_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: SubjectFindingRepository = Depends(get_subject_finding_repo),
    current_user=Depends(get_current_user),
):
    if subject_consistency_run_id:
        return await repo.list_by_run(db, subject_consistency_run_id)
    return await repo.list(db)


@router.post("/", response_model=SubjectFindingRead)
async def create_subject_finding(
    payload: SubjectFindingCreate,
    db: AsyncSession = Depends(get_db),
    repo: SubjectFindingRepository = Depends(get_subject_finding_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{finding_id}", response_model=SubjectFindingRead)
async def get_subject_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: SubjectFindingRepository = Depends(get_subject_finding_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, finding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject finding not found")
    return item


@router.patch("/{finding_id}", response_model=SubjectFindingRead)
async def update_subject_finding(
    finding_id: UUID,
    payload: SubjectFindingUpdate,
    db: AsyncSession = Depends(get_db),
    repo: SubjectFindingRepository = Depends(get_subject_finding_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, finding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject finding not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{finding_id}")
async def delete_subject_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: SubjectFindingRepository = Depends(get_subject_finding_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, finding_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject finding not found")
    await repo.delete(db, item)
    return {"message": "Subject finding deleted"}
