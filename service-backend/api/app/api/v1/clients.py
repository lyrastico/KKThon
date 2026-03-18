from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
import app.repositories.client as client_repo
import app.repositories.user as user_repo

router = APIRouter(prefix="/clients", tags=["clients"])


def _uid(current_user) -> UUID:
    return UUID(str(current_user.id))


async def _ensure_user_row(db: AsyncSession, current_user):
    uid = _uid(current_user)
    u = await user_repo.get_user(db, uid)
    if not u:
        meta = getattr(current_user, "user_metadata", None) or {}
        u = await user_repo.upsert_user_from_auth(
            db,
            user_id=uid,
            email=getattr(current_user, "email", None),
            fullname=meta.get("full_name") or meta.get("fullname"),
        )
    return u


@router.get("", response_model=list[ClientRead])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    await _ensure_user_row(db, current_user)
    return await client_repo.list_clients_for_user(db, _uid(current_user), skip=skip, limit=limit)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await _ensure_user_row(db, current_user)
    return await client_repo.create_client(db, _uid(current_user), payload.client_name)


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return c


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if payload.client_name is None:
        return c
    return await client_repo.update_client(db, c, payload.client_name)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    await client_repo.delete_client(db, c)
    return None
