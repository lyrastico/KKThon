from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.clients import router as clients_router
from app.api.v1.files import router as files_router
from app.api.v1.conformity_reports import router as conformity_reports_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/v1")
api_router.include_router(users_router, prefix="/v1")
api_router.include_router(clients_router, prefix="/v1")
api_router.include_router(files_router, prefix="/v1")
api_router.include_router(conformity_reports_router, prefix="/v1")
