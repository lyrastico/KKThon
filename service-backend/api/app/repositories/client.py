from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client import Client


async def get_client(db: AsyncSession, client_id: UUID) -> Client | None:
    r = await db.execute(select(Client).where(Client.client_id == client_id))
    return r.scalar_one_or_none()


async def list_clients_for_user(db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100):
    r = await db.execute(
        select(Client).where(Client.user_id == user_id).offset(skip).limit(limit)
    )
    return r.scalars().all()


async def create_client(db: AsyncSession, user_id: UUID, client_name: str) -> Client:
    c = Client(user_id=user_id, client_name=client_name)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


async def update_client(db: AsyncSession, c: Client, client_name: str) -> Client:
    c.client_name = client_name
    await db.commit()
    await db.refresh(c)
    return c


async def delete_client(db: AsyncSession, c: Client) -> None:
    await db.delete(c)
    await db.commit()
