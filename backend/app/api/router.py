from fastapi import APIRouter
from app.api.v1.analysis_findings import router as analysis_findings_router
from app.api.v1.analysis_runs import router as analysis_runs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.document_events import router as document_events_router
from app.api.v1.document_files import router as document_files_router
from app.api.v1.documents import router as documents_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.subject_consistency_runs import router as subject_consistency_runs_router
from app.api.v1.subject_findings import router as subject_findings_router
from app.api.v1.subjects import router as subjects_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router, prefix="/v1")
api_router.include_router(organizations_router, prefix="/v1")
api_router.include_router(subjects_router, prefix="/v1")
api_router.include_router(documents_router, prefix="/v1")
api_router.include_router(document_files_router, prefix="/v1")
api_router.include_router(document_events_router, prefix="/v1")
api_router.include_router(analysis_runs_router, prefix="/v1")
api_router.include_router(analysis_findings_router, prefix="/v1")
api_router.include_router(subject_consistency_runs_router, prefix="/v1")
api_router.include_router(subject_findings_router, prefix="/v1")
