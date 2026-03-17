import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class SubjectConsistencyRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "subject_consistency_runs"

    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    input_analysis_run_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    gold_output: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))