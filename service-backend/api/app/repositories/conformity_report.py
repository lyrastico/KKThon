from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conformity_report import ConformityReport


async def get_report(db: AsyncSession, report_id: UUID) -> ConformityReport | None:
    r = await db.execute(select(ConformityReport).where(ConformityReport.report_id == report_id))
    return r.scalar_one_or_none()


async def list_reports_for_client(db: AsyncSession, client_id: UUID, skip: int = 0, limit: int = 100):
    r = await db.execute(
        select(ConformityReport)
        .where(ConformityReport.client_id == client_id)
        .offset(skip)
        .limit(limit)
    )
    return r.scalars().all()


async def create_report(
    db: AsyncSession,
    *,
    client_id: UUID,
    gold_content: dict | None,
    s3_gold_path: str | None,
    silver_content: dict | None,
    processing_status: str,
) -> ConformityReport:
    r = ConformityReport(
        client_id=client_id,
        gold_content=gold_content,
        s3_gold_path=s3_gold_path,
        silver_content=silver_content,
        processing_status=processing_status,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def update_report(db: AsyncSession, r: ConformityReport, data: dict) -> ConformityReport:
    for k, v in data.items():
        if v is not None or k in ("gold_content", "silver_content", "s3_gold_path"):
            setattr(r, k, v)
    await db.commit()
    await db.refresh(r)
    return r


async def delete_report(db: AsyncSession, r: ConformityReport) -> None:
    await db.delete(r)
    await db.commit()
