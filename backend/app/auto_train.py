"""Automatic training checks; artifacts and watermarks persist in PostgreSQL."""
import asyncio
from datetime import datetime, timezone
import hashlib
import logging
from uuid import uuid4

from sqlalchemy import func, select, text
from app.config import settings
from app.database import SessionLocal
from app.forecasting import fit_model, InsufficientData, compatible_artifact, TARGETS
from app.model_queries import latest_model
from app.models import ForecastModel, Measurement

logger = logging.getLogger(__name__)


def train_device(db, device_id, now, target="soil_raw"):
    # Transaction-scoped advisory lock avoids duplicate automatic training across
    # API workers using the same PostgreSQL database. No network lock in SQLite QA.
    if db.get_bind().dialect.name == "postgresql":
        lock_id = int.from_bytes(hashlib.sha256((device_id+":"+target).encode()).digest()[:8], "big", signed=True)
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_id}):
            return "locked"
    latest = latest_model(db, device_id, target)
    if latest and compatible_artifact(latest.artifact, target):
        if (now - latest.trained_at).total_seconds() < settings.ml_retrain_seconds:
            return "cooldown"
        watermark = latest.artifact.get("source_max_id", 0)
        count = db.scalar(select(func.count()).select_from(Measurement).where(
            Measurement.device_id == device_id, Measurement.id > watermark))
        if count < settings.ml_min_new_samples:
            return "waiting_new_data"
    max_id = db.scalar(select(func.max(Measurement.id)).where(Measurement.device_id == device_id))
    rows = db.scalars(select(Measurement).where(Measurement.device_id == device_id,
                      Measurement.id <= max_id).order_by(Measurement.measured_at.desc(), Measurement.id.desc())
                      .limit(100000)).all() if max_id else []
    try:
        artifact = fit_model(rows, now, target)
    except InsufficientData:
        return "insufficient_data"
    # Do not create versions when only incomplete minutes or invalid samples changed.
    if latest and latest.artifact.get("dataset_sha256") == artifact["dataset_sha256"]:
        return "unchanged_dataset"
    artifact.update(source_max_id=max_id, source_rows=len(rows), source_limit=100000,
                    source_limit_reached=len(rows) == 100000, training_mode="automatic")
    db.add(ForecastModel(id=str(uuid4()), device_id=device_id, trained_at=now, artifact=artifact))
    db.commit()
    return "trained"


def run_cycle():
    try:
        with SessionLocal() as db:
            devices = list(db.scalars(select(Measurement.device_id).distinct()))
    except Exception as exc:
        logger.warning("Consulta do treino automático falhou (%s)", type(exc).__name__)
        return
    for device in devices:
        try:
            for target in TARGETS:
                with SessionLocal() as db:
                    result = train_device(db, device, datetime.now(timezone.utc), target)
                    logger.info("Treino automático: dispositivo=%s alvo=%s estado=%s", device, target, result)
        except Exception as exc:
            # Connection errors may contain credentials; log only the exception type.
            logger.warning("Treino automático falhou (%s)", type(exc).__name__)


async def training_loop():
    # The worker performs one training cycle at a time, outside the HTTP event loop.
    while True:
        await asyncio.to_thread(run_cycle)
        await asyncio.sleep(settings.ml_check_seconds)
