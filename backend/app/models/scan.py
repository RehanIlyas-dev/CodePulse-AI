import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class CodeScan(Base):
    # Mapping the pydantic model to the database table
    __tablename__ = "code_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(50), default="python")
    raw_code: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Store AST metrics and issues list as structured JSONB
    ast_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    issues_list: Mapped[list] = mapped_column(JSONB, nullable=False)
    
    time_complexity: Mapped[str] = mapped_column(String(50), nullable=False)
    space_complexity: Mapped[str] = mapped_column(String(50), nullable=False)
    security_score: Mapped[int] = mapped_column(Integer, nullable=False)
    maintainability_score: Mapped[int] = mapped_column(Integer, nullable=False)
    refactored_code: Mapped[str] = mapped_column(Text, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)