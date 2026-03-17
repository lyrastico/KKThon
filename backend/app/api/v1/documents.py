from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_document_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentRead])
async def list_documents(
    subject_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    if subject_id:
        return await repo.list_by_subject(db, subject_id)
    return await repo.list(db)


@router.post("/", response_model=DocumentRead)
async def create_document(
    payload: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")
    return item


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document not found")
    await repo.delete(db, item)
    return {"message": "Document deleted"}