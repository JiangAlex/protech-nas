"""Metrics model — periodic system metrics for history charts."""

from datetime import datetime
from sqlalchemy import Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class MetricsRecord(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)
    disk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_rx_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network_tx_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
