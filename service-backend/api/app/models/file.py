import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class FileRecord(Base):
    __tablename__ = "files"

    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    s3_raw_path: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    s3_silver_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    silver_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_format: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client: Mapped["Client"] = relationship("Client", back_populates="files")
