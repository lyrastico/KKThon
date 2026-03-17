from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.profile import Profile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self):
        super().__init__(Profile)

    async def get_by_email(self, db: AsyncSession, email: str):
        result = await db.execute(select(Profile).where(Profile.email == email))
        return result.scalar_one_or_none()
