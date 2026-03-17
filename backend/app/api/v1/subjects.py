from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_subject_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.subject import SubjectRepository
from app.schemas.subject import SubjectCreate, SubjectRead, SubjectUpdate

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("/", response_model=list[SubjectRead])
async def list_subjects(
    organization_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: SubjectRepository = Depends(get_subject_repo),
    current_user=Depends(get_current_user),
):
    if organization_id:
        return await repo.list_by_organization(db, organization_id)
    return await repo.list(db)


@router.post("/", response_model=SubjectRead)
async def create_subject(
    payload: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    repo: SubjectRepository = Depends(get_subject_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{subject_id}", response_model=SubjectRead)
async def get_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: SubjectRepository = Depends(get_subject_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, subject_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject not found")
    return item


@router.patch("/{subject_id}", response_model=SubjectRead)
async def update_subject(
    subject_id: UUID,
    payload: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    repo: SubjectRepository = Depends(get_subject_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, subject_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{subject_id}")
async def delete_subject(
    subject_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: SubjectRepository = Depends(get_subject_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, subject_id)
    if not item:
        raise HTTPException(status_code=404, detail="Subject not found")
    await repo.delete(db, item)
    return {"message": "Subject deleted"}