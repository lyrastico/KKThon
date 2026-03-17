from app.repositories.organization import OrganizationRepository
from app.repositories.subject import SubjectRepository
from app.repositories.document import DocumentRepository


def get_organization_repo():
    return OrganizationRepository()


def get_subject_repo():
    return SubjectRepository()


def get_document_repo():
    return DocumentRepository()