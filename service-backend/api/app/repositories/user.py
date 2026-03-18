from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    r = await db.execute(select(User).where(User.user_id == user_id))
    return r.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    user_id: UUID,
    email: str | None,
    fullname: str | None,
) -> User:
    u = User(user_id=user_id, email=email, fullname=fullname)
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def update_user(db: AsyncSession, u: User, data: dict) -> User:
    for k, v in data.items():
        if v is not None:
            setattr(u, k, v)
    await db.commit()
    await db.refresh(u)
    return u


async def delete_user(db: AsyncSession, u: User) -> None:
    await db.delete(u)
    await db.commit()


async def upsert_user_from_auth(
    db: AsyncSession,
    *,
    user_id: UUID,
    email: str | None,
    fullname: str | None,
) -> User:
    existing = await get_user(db, user_id)
    if existing:
        if email is not None:
            existing.email = email
        if fullname is not None:
            existing.fullname = fullname
        await db.commit()
        await db.refresh(existing)
        return existing
    return await create_user(db, user_id=user_id, email=email, fullname=fullname)
