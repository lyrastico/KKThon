import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ConformityReport(Base):
    __tablename__ = "conformity_reports"

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    gold_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    s3_gold_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    silver_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client: Mapped["Client"] = relationship("Client", back_populates="reports")
