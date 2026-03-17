from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_subject_consistency_run_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.subject_consistency_run import SubjectConsistencyRunRepository
from app.schemas.subject_consistency_run import (
    SubjectConsistencyRunCreate,
    SubjectConsistencyRunRead,
    SubjectConsistencyRunUpdate,
)

router = APIRouter(prefix="/subject-consistency-runs", tags=["subject-consistency-runs"])


@router.get("/", response_model=list[SubjectConsistencyRunRead])
async def list_subject_consistency_runs(
    subject_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: SubjectConsistencyRunRepository = Depends(get_subject_consistency_run_repo),
    current_user=Depends(get_current_user),
):
    if subject_id:
        return await repo.list_by_subject(db, subject_id)
    return await repo.list(db)


@router.post("/", response_model=SubjectConsistencyRunRead)
async def create_subject_consistency_run(
    payload: SubjectConsistencyRunCreate,
    db: AsyncSession = Depends(get_db),
    repo: SubjectConsistencyRunRepository = Depends(get_subject_consistency_run_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{run_id}", response_model=SubjectConsistencyRunRead)
async def get_subject_consistency_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: SubjectConsistencyRunRepository = Depends(get_subject_consistency_run_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject consistency run not found")
    return item


@router.patch("/{run_id}", response_model=SubjectConsistencyRunRead)
async def update_subject_consistency_run(
    run_id: UUID,
    payload: SubjectConsistencyRunUpdate,
    db: AsyncSession = Depends(get_db),
    repo: SubjectConsistencyRunRepository = Depends(get_subject_consistency_run_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject consistency run not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{run_id}")
async def delete_subject_consistency_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: SubjectConsistencyRunRepository = Depends(get_subject_consistency_run_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject consistency run not found")
    await repo.delete(db, item)
    return {"message": "Subject consistency run deleted"}
