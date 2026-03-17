from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.subject import SubjectRepository
from app.schemas.subject import SubjectCreate, SubjectRead

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectRead])
async def list_subjects(db: AsyncSession = Depends(get_db)):
    return await SubjectRepository(db).list()


@router.post("", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
async def create_subject(payload: SubjectCreate, db: AsyncSession = Depends(get_db)):
    return await SubjectRepository(db).create(payload)
