import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    client_name: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="clients")
    files: Mapped[list["FileRecord"]] = relationship(
        "FileRecord", back_populates="client", cascade="all, delete-orphan"
    )
    reports: Mapped[list["ConformityReport"]] = relationship(
        "ConformityReport", back_populates="client", cascade="all, delete-orphan"
    )
