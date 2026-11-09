from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, DateTime, Float, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator
from app.database import Base


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            # SQLite test database drops timezone information; values are stored in UTC.
            return value.replace(tzinfo=timezone.utc)
        return value


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint("air_humidity_pct >= 0 AND air_humidity_pct <= 100"),
        CheckConstraint("soil_raw >= 0"),
        Index("ix_measurements_device_time", "device_id", "measured_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64))
    temperature_c: Mapped[float] = mapped_column(Float)
    air_humidity_pct: Mapped[float] = mapped_column(Float)
    soil_raw: Mapped[int]
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    received_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class ForecastModel(Base):
    __tablename__ = "forecast_models"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    trained_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    artifact: Mapped[dict] = mapped_column(JSON)
