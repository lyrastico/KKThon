from fastapi import APIRouter
from app.api.v1.organizations import router as organizations_router
from app.api.v1.subjects import router as subjects_router
from app.api.v1.documents import router as documents_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(organizations_router)
api_router.include_router(subjects_router)
api_router.include_router(documents_router)
