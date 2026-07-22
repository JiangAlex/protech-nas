"""ShareLink model — file sharing via public links."""

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    link_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    max_downloads: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
