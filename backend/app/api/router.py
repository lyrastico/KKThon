from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.subjects import router as subjects_router
from app.api.v1.documents import router as documents_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/v1")
api_router.include_router(organizations_router, prefix="/v1")
api_router.include_router(subjects_router, prefix="/v1")
api_router.include_router(documents_router, prefix="/v1")