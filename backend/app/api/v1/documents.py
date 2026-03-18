from pathlib import Path
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_document_repo,
    get_document_file_repo,
    get_profile_repo,
)
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.document import DocumentRepository
from app.repositories.document_file import DocumentFileRepository
from app.repositories.profile import ProfileRepository
from app.schemas.document import DocumentCreate, DocumentRead, DocumentUpdate
from app.services.s3 import upload_bytes_to_s3

router = APIRouter(prefix="/documents", tags=["documents"])


async def ensure_profile_exists(db: AsyncSession, profile_repo: ProfileRepository, current_user):
    profile = await profile_repo.get(db, current_user.id)
    if profile:
        return profile

    payload = {
        "id": current_user.id,
        "email": getattr(current_user, "email", None),
        "full_name": getattr(current_user, "full_name", None)
        or getattr(current_user, "user_metadata", {}).get("full_name", ""),
        "is_active": True,
    }
    return await profile_repo.create(db, payload)


@router.get("/", response_model=list[DocumentRead])
async def list_documents(
    subject_id: str | None = Query(default=None),
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
    document_id: str,
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    document = await repo.get(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.patch("/{document_id}", response_model=DocumentRead)
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    repo: DocumentRepository = Depends(get_document_repo),
    current_user=Depends(get_current_user),
):
    document = await repo.get(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return await repo.update_from_schema(db, document, payload)


@router.post("/upload", response_model=DocumentRead)
async def upload_document(
    organization_id: str = Form(...),
    subject_id: str = Form(...),
    title: str = Form(...),
    document_type_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    document_repo: DocumentRepository = Depends(get_document_repo),
    document_file_repo: DocumentFileRepository = Depends(get_document_file_repo),
    profile_repo: ProfileRepository = Depends(get_profile_repo),
    current_user=Depends(get_current_user),
):
    await ensure_profile_exists(db, profile_repo, current_user)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    file_hash = hashlib.sha256(content).hexdigest()
    extension = Path(file.filename).suffix.lower().lstrip(".")
    hashed_filename = f"{file_hash}.{extension}" if extension else file_hash

    document_payload = DocumentCreate(
        organization_id=organization_id,
        subject_id=subject_id,
        document_type_id=document_type_id,
        title=title,
        status="uploaded",
        compliance_status=None,
        review_status=None,
        uploaded_by=current_user.id,
        metadata={},
    )
    document = await document_repo.create_from_schema(db, document_payload)

    storage_bucket = settings.s3_bucket_name
    storage_path = f"{settings.s3_key_prefix}/{hashed_filename}"

    try:
        upload_bytes_to_s3(
            content=content,
            bucket_name=storage_bucket,
            object_key=storage_path,
            content_type=file.content_type,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}") from exc

    document_file = await document_file_repo.create(
        db,
        {
            "document_id": document.id,
            "storage_bucket": storage_bucket,
            "storage_path": storage_path,
            "original_filename": file.filename,
            "mime_type": file.content_type,
            "extension": extension or None,
            "size_bytes": len(content),
            "sha256": file_hash,
            "page_count": None,
            "version_no": 1,
            "upload_status": "uploaded",
            "uploaded_by": current_user.id,
        },
    )

    document = await document_repo.update(
        db,
        document,
        {
            "current_file_id": document_file.id,
            "status": "uploaded",
        },
    )

    return document