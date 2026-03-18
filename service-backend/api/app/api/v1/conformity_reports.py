from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.conformity_report import (
    ConformityReportCreate,
    ConformityReportRead,
    ConformityReportUpdate,
)
import app.repositories.client as client_repo
import app.repositories.conformity_report as report_repo

router = APIRouter(prefix="/conformity-reports", tags=["conformity-reports"])


def _uid(current_user) -> UUID:
    return UUID(str(current_user.id))


async def _client_owned(db, client_id: UUID, current_user):
    c = await client_repo.get_client(db, client_id)
    if not c or c.user_id != _uid(current_user):
        return None
    return c


@router.get("", response_model=list[ConformityReportRead])
async def list_reports(
    client_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    if not await _client_owned(db, client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return await report_repo.list_reports_for_client(db, client_id, skip=skip, limit=limit)


@router.post("", response_model=ConformityReportRead, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ConformityReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not await _client_owned(db, payload.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return await report_repo.create_report(
        db,
        client_id=payload.client_id,
        gold_content=payload.gold_content,
        s3_gold_path=payload.s3_gold_path,
        silver_content=payload.silver_content,
        processing_status=payload.processing_status,
    )


@router.get("/{report_id}", response_model=ConformityReportRead)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not await _client_owned(db, r.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return r


@router.patch("/{report_id}", response_model=ConformityReportRead)
async def update_report(
    report_id: UUID,
    payload: ConformityReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not await _client_owned(db, r.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    data = payload.model_dump(exclude_unset=True)
    return await report_repo.update_report(db, r, data)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = await report_repo.get_report(db, report_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not await _client_owned(db, r.client_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    await report_repo.delete_report(db, r)
    return None
