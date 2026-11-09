from datetime import datetime, timedelta, timezone
import math
import os
os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('INGEST_API_KEY', 'test-key')
os.environ['ML_AUTO_TRAIN_ENABLED'] = 'false'

import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.auto_train import train_device
from app.config import settings
from app.database import Base
from app.models import ForecastModel, Measurement

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)

@pytest.fixture
def db():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_empty_history_waits_without_creating_model(db):
    assert train_device(db, 'esp32-01', NOW) == 'insufficient_data'
    assert db.scalar(select(func.count()).select_from(ForecastModel)) == 0


def test_automatic_train_cooldown_and_new_data_gate(db, monkeypatch):
    monkeypatch.setattr(settings, 'ml_retrain_seconds', 3600)
    monkeypatch.setattr(settings, 'ml_min_new_samples', 120)
    for i in range(400):
        at = NOW - timedelta(minutes=400-i)
        db.add(Measurement(device_id='esp32-01', measured_at=at, received_at=at,
            temperature_c=24+math.sin(i/30), air_humidity_pct=60,
            soil_raw=round(3500+100*math.sin(i/30))))
    db.commit()
    assert train_device(db, 'esp32-01', NOW) == 'trained'
    model = db.scalar(select(ForecastModel))
    assert model.artifact['training_mode'] == 'automatic'
    assert model.artifact['algorithm'] == 'RandomForestRegressor'
    assert model.artifact['source_max_id'] == 400
    assert train_device(db, 'esp32-01', NOW+timedelta(minutes=10)) == 'cooldown'
    assert train_device(db, 'esp32-01', NOW+timedelta(hours=2)) == 'waiting_new_data'
    assert db.scalar(select(func.count()).select_from(ForecastModel)) == 1
