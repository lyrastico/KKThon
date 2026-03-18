from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file import FileRecord


async def get_file(db: AsyncSession, file_id: UUID) -> FileRecord | None:
    r = await db.execute(select(FileRecord).where(FileRecord.file_id == file_id))
    return r.scalar_one_or_none()


async def get_file_by_s3_raw_path(db: AsyncSession, s3_raw_path: str) -> FileRecord | None:
    r = await db.execute(select(FileRecord).where(FileRecord.s3_raw_path == s3_raw_path))
    return r.scalar_one_or_none()


async def list_files_for_client(db: AsyncSession, client_id: UUID, skip: int = 0, limit: int = 100):
    r = await db.execute(
        select(FileRecord).where(FileRecord.client_id == client_id).offset(skip).limit(limit)
    )
    return r.scalars().all()


async def create_file(
    db: AsyncSession,
    *,
    client_id: UUID,
    original_filename: str,
    s3_raw_path: str,
    file_format: str | None,
    processing_status: str = "pending",
) -> FileRecord:
    f = FileRecord(
        client_id=client_id,
        original_filename=original_filename,
        s3_raw_path=s3_raw_path,
        file_format=file_format,
        processing_status=processing_status,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return f


async def update_file(db: AsyncSession, f: FileRecord, data: dict) -> FileRecord:
    for k, v in data.items():
        if v is not None or k in ("s3_silver_path", "silver_content", "type"):
            setattr(f, k, v)
    await db.commit()
    await db.refresh(f)
    return f


async def delete_file(db: AsyncSession, f: FileRecord) -> None:
    await db.delete(f)
    await db.commit()
