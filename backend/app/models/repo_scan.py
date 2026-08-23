import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class RepoScan(Base):
    # Mapping the repository analysis result to a database table
    __tablename__ = "repo_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    source: Mapped[str] = mapped_column(String(255), nullable=False)  # github url or "zip upload"

    # Store structured repo analysis as JSONB
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False)
    dependency_graph: Mapped[dict] = mapped_column(JSONB, nullable=False)
    files: Mapped[dict] = mapped_column(JSONB, nullable=False)

    architecture_score: Mapped[int] = mapped_column(Integer, nullable=False)
    maintainability_score: Mapped[int] = mapped_column(Integer, nullable=False)
    refactored_suggestions: Mapped[str] = mapped_column(Text, nullable=False)
    issues_list: Mapped[list] = mapped_column(JSONB, default=list)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)