from .auth import router as auth_router
from .organizations import router as organizations_router
from .subjects import router as subjects_router
from .documents import router as documents_router
from .document_files import router as document_files_router
from .analysis_runs import router as analysis_runs_router
from .analysis_findings import router as analysis_findings_router
from .subject_consistency_runs import router as subject_consistency_runs_router
from .subject_findings import router as subject_findings_router
from .document_events import router as document_events_router

__all__ = [
    "auth_router",
    "organizations_router",
    "subjects_router",
    "documents_router",
    "document_files_router",
    "analysis_runs_router",
    "analysis_findings_router",
    "subject_consistency_runs_router",
    "subject_findings_router",
    "document_events_router",
]
