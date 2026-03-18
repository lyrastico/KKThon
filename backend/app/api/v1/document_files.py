from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_document_file_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.document_file import DocumentFileRepository
from app.schemas.document_file import DocumentFileCreate, DocumentFileRead, DocumentFileUpdate

router = APIRouter(prefix="/document-files", tags=["document-files"])


@router.get("/", response_model=list[DocumentFileRead])
async def list_document_files(
    document_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: DocumentFileRepository = Depends(get_document_file_repo),
    current_user=Depends(get_current_user),
):
    if document_id:
        return await repo.list_by_document(db, document_id)
    return await repo.list(db)


@router.post("/", response_model=DocumentFileRead)
async def create_document_file(
    payload: DocumentFileCreate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentFileRepository = Depends(get_document_file_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{document_file_id}", response_model=DocumentFileRead)
async def get_document_file(
    document_file_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: DocumentFileRepository = Depends(get_document_file_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document file not found")
    return item


@router.patch("/{document_file_id}", response_model=DocumentFileRead)
async def update_document_file(
    document_file_id: UUID,
    payload: DocumentFileUpdate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentFileRepository = Depends(get_document_file_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document file not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{document_file_id}")
async def delete_document_file(
    document_file_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: DocumentFileRepository = Depends(get_document_file_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document file not found")
    await repo.delete(db, item)
    return {"message": "Document file deleted"}
