import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_user_provider_id"),
    )

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = mapped_column(String, unique=True, index=True, nullable=False)
    name = mapped_column(String, nullable=True)
    avatar_url = mapped_column(String, nullable=True)
    provider = mapped_column(String, nullable=False)
    provider_id = mapped_column(String, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
