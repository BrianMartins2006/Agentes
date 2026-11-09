from datetime import datetime, timedelta, timezone
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("INGEST_API_KEY", "test-key")

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.daily_check import check_history
from app.database import Base
from app.models import Measurement


NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_sample(db, device_id, received_at):
    db.add(Measurement(device_id=device_id, temperature_c=25, air_humidity_pct=60,
                       soil_raw=3500, measured_at=received_at, received_at=received_at))
    db.commit()


def test_empty_history_does_not_create_measurements(db):
    result = check_history(db, "esp32-01", NOW, 300)
    assert result["database"] == "ok"
    assert result["status"] == "sem_dados"
    assert result["measurements_received_24h"] == 0
    assert result["last_received_at"] is None
    assert db.scalar(select(func.count()).select_from(Measurement)) == 0


def test_daily_window_device_filter_and_freshness(db):
    add_sample(db, "esp32-01", NOW - timedelta(days=2))
    add_sample(db, "esp32-01", NOW - timedelta(hours=2))
    add_sample(db, "esp32-01", NOW - timedelta(seconds=60))
    add_sample(db, "other", NOW)
    result = check_history(db, "esp32-01", NOW, 300)
    assert result["status"] == "atualizado"
    assert result["measurements_received_24h"] == 2
    assert result["last_received_at"] == (NOW - timedelta(seconds=60)).isoformat()


def test_old_or_future_data_is_not_reported_as_current(db):
    add_sample(db, "old", NOW - timedelta(hours=1))
    add_sample(db, "future", NOW + timedelta(hours=1))
    assert check_history(db, "old", NOW, 300)["status"] == "desatualizado"
    result = check_history(db, "future", NOW, 300)
    assert result["status"] == "horario_inconsistente"
    assert result["measurements_received_24h"] == 0
