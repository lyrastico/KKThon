from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_document_event_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.document_event import DocumentEventRepository
from app.schemas.document_event import DocumentEventCreate, DocumentEventRead, DocumentEventUpdate

router = APIRouter(prefix="/document-events", tags=["document-events"])


@router.get("/", response_model=list[DocumentEventRead])
async def list_document_events(
    document_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    repo: DocumentEventRepository = Depends(get_document_event_repo),
    current_user=Depends(get_current_user),
):
    if document_id:
        return await repo.list_by_document(db, document_id)
    return await repo.list(db)


@router.post("/", response_model=DocumentEventRead)
async def create_document_event(
    payload: DocumentEventCreate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentEventRepository = Depends(get_document_event_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create_from_schema(db, payload)


@router.get("/{document_event_id}", response_model=DocumentEventRead)
async def get_document_event(
    document_event_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: DocumentEventRepository = Depends(get_document_event_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_event_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document event not found")
    return item


@router.patch("/{document_event_id}", response_model=DocumentEventRead)
async def update_document_event(
    document_event_id: UUID,
    payload: DocumentEventUpdate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentEventRepository = Depends(get_document_event_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_event_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document event not found")
    return await repo.update_from_schema(db, item, payload)


@router.delete("/{document_event_id}")
async def delete_document_event(
    document_event_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: DocumentEventRepository = Depends(get_document_event_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, document_event_id)
    if not item:
        raise HTTPException(status_code=404, detail="Document event not found")
    await repo.delete(db, item)
    return {"message": "Document event deleted"}
