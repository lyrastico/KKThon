from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_organization_repo
from app.core.security import get_current_user
from app.db.session import get_db
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/", response_model=list[OrganizationRead])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    repo: OrganizationRepository = Depends(get_organization_repo),
    current_user=Depends(get_current_user),
):
    return await repo.list(db)


@router.post("/", response_model=OrganizationRead)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    repo: OrganizationRepository = Depends(get_organization_repo),
    current_user=Depends(get_current_user),
):
    return await repo.create(db, payload.model_dump())


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: OrganizationRepository = Depends(get_organization_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Organization not found")
    return item


@router.patch("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    repo: OrganizationRepository = Depends(get_organization_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Organization not found")
    return await repo.update(db, item, payload.model_dump(exclude_unset=True))


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    repo: OrganizationRepository = Depends(get_organization_repo),
    current_user=Depends(get_current_user),
):
    item = await repo.get(db, organization_id)
    if not item:
        raise HTTPException(status_code=404, detail="Organization not found")
    await repo.delete(db, item)
    return {"message": "Organization deleted"}