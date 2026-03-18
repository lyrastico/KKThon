from app.repositories.organization import OrganizationRepository
from app.repositories.subject import SubjectRepository
from app.repositories.document import DocumentRepository
from app.repositories.profile import ProfileRepository

from app.repositories.document_file import DocumentFileRepository
from app.repositories.analysis_run import AnalysisRunRepository
from app.repositories.analysis_finding import AnalysisFindingRepository
from app.repositories.subject_consistency_run import SubjectConsistencyRunRepository
from app.repositories.subject_finding import SubjectFindingRepository
from app.repositories.document_event import DocumentEventRepository


def get_organization_repo() -> OrganizationRepository:
    return OrganizationRepository()


def get_subject_repo() -> SubjectRepository:
    return SubjectRepository()


def get_document_repo() -> DocumentRepository:
    return DocumentRepository()


def get_profile_repo() -> ProfileRepository:
    return ProfileRepository()


def get_document_file_repo() -> DocumentFileRepository:
    return DocumentFileRepository()


def get_analysis_run_repo() -> AnalysisRunRepository:
    return AnalysisRunRepository()


def get_analysis_finding_repo() -> AnalysisFindingRepository:
    return AnalysisFindingRepository()


def get_subject_consistency_run_repo() -> SubjectConsistencyRunRepository:
    return SubjectConsistencyRunRepository()


def get_subject_finding_repo() -> SubjectFindingRepository:
    return SubjectFindingRepository()


def get_document_event_repo() -> DocumentEventRepository:
    return DocumentEventRepository()
