from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.file import FileCreate, FileRead, FileUpdate
from app.services import s3 as s3svc
import app.repositories.client as client_repo
import app.repositories.file as file_repo
import app.repositories.user as user_repo

router = APIRouter(prefix="/files", tags=["files"])


def _uid(current_user) -> UUID:
    return UUID(str(current_user.id))


async def _ensure_user_row(db: AsyncSession, current_user):
    uid = _uid(current_user)
    u = await user_repo.get_user(db, uid)
    if not u:
        meta = getattr(current_user, "user_metadata", None) or {}
        await user_repo.upsert_user_from_auth(
            db,
            user_id=uid,
            email=getattr(current_user, "email", None),
            fullname=meta.get("full_name") or meta.get("fullname"),
        )


async def _get_owned_client(db, client_id: UUID, current_user):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        return None
    return c


@router.post("/upload", response_model=FileRead)
async def upload_file(
    client_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _ensure_user_row(db, current_user)
    c = await _get_owned_client(db, client_id, current_user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    ct = file.content_type
    original = file.filename or "upload"

    try:
        key = s3svc.upload_raw_file(
            content, original_filename=original, content_type=ct
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    fmt = s3svc.guess_extension(original, ct)
    try:
        f = await file_repo.create_file(
            db,
            client_id=client_id,
            original_filename=original,
            s3_raw_path=key,
            file_format=fmt,
            processing_status="pending",
        )
        return f
    except IntegrityError:
        await db.rollback()
        existing = await file_repo.get_file_by_s3_raw_path(db, key)
        if existing:
            return existing
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate key")


@router.get("", response_model=list[FileRead])
async def list_files(
    client_id: UUID = Query(..., description="Filtrer par client"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    c = await _get_owned_client(db, client_id, current_user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return await file_repo.list_files_for_client(db, client_id, skip=skip, limit=limit)


@router.post("", response_model=FileRead, status_code=status.HTTP_201_CREATED)
async def create_file_manual(
    payload: FileCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Création manuelle (ex. si fichier déjà sur S3)."""
    c = await _get_owned_client(db, payload.client_id, current_user)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    try:
        return await file_repo.create_file(
            db,
            client_id=payload.client_id,
            original_filename=payload.original_filename,
            s3_raw_path=payload.s3_raw_path,
            file_format=payload.file_format,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="s3_raw_path already exists")


@router.get("/{file_id}", response_model=FileRead)
async def get_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    f = await file_repo.get_file(db, file_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    c = await client_repo.get_client(db, f.client_id)
    if not c or c.user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return f


@router.patch("/{file_id}", response_model=FileRead)
async def update_file(
    file_id: UUID,
    payload: FileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    f = await file_repo.get_file(db, file_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    c = await client_repo.get_client(db, f.client_id)
    if not c or c.user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    data = payload.model_dump(exclude_unset=True)
    return await file_repo.update_file(db, f, data)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    f = await file_repo.get_file(db, file_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    c = await client_repo.get_client(db, f.client_id)
    if not c or c.user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    await file_repo.delete_file(db, f)
    return None
