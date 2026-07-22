"""Backup models — task definitions and execution history."""

from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class BackupTask(Base):
    __tablename__ = "backup_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(1024), nullable=False)
    destination: Mapped[str] = mapped_column(String(1024), nullable=False)
    schedule: Mapped[str | None] = mapped_column(String(64), nullable=True)  # cron expression
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    method: Mapped[str] = mapped_column(String(16), default="rsync")  # rsync / borg / restic
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(16), nullable=True)  # success / failed / running
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BackupHistory(Base):
    __tablename__ = "backup_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # success / failed
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    files_transferred: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
