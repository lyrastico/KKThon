from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.user import UserRead, UserUpdate
import app.repositories.user as user_repo

router = APIRouter(prefix="/users", tags=["users"])


def _uid(current_user) -> UUID:
    return UUID(str(current_user.id))


def _fullname_from_auth(current_user) -> str | None:
    meta = getattr(current_user, "user_metadata", None) or {}
    return meta.get("full_name") or meta.get("fullname")


@router.post("/sync", response_model=UserRead)
async def sync_user(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Assure une ligne public.users pour le JWT (utile si trigger auth pas encore appliqué)."""
    uid = _uid(current_user)
    u = await user_repo.upsert_user_from_auth(
        db,
        user_id=uid,
        email=getattr(current_user, "email", None),
        fullname=_fullname_from_auth(current_user),
    )
    return u


@router.get("/me", response_model=UserRead)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = _uid(current_user)
    u = await user_repo.get_user(db, uid)
    if not u:
        u = await user_repo.upsert_user_from_auth(
            db,
            user_id=uid,
            email=getattr(current_user, "email", None),
            fullname=_fullname_from_auth(current_user),
        )
    return u


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Liste limitée : uniquement l’utilisateur connecté."""
    uid = _uid(current_user)
    u = await user_repo.get_user(db, uid)
    if not u:
        u = await user_repo.upsert_user_from_auth(
            db,
            user_id=uid,
            email=getattr(current_user, "email", None),
            fullname=_fullname_from_auth(current_user),
        )
    return [u]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if user_id != _uid(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    u = await user_repo.get_user(db, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u


@router.patch("/me", response_model=UserRead)
async def patch_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = _uid(current_user)
    u = await user_repo.get_user(db, uid)
    if not u:
        u = await user_repo.upsert_user_from_auth(
            db,
            user_id=uid,
            email=getattr(current_user, "email", None),
            fullname=_fullname_from_auth(current_user),
        )
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return u
    return await user_repo.update_user(db, u, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = _uid(current_user)
    u = await user_repo.get_user(db, uid)
    if u:
        await user_repo.delete_user(db, u)
    return None
