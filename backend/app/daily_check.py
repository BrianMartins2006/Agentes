"""Consult real historical data; never insert artificial measurements."""

import argparse
from datetime import datetime, timedelta, timezone
import json

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Measurement


def check_history(db: Session, device_id: str, now: datetime, max_age_seconds: int) -> dict:
    if now.tzinfo is None or max_age_seconds <= 0:
        raise ValueError("Informe horário com fuso e limite de atraso positivo")
    count = db.scalar(select(func.count()).select_from(Measurement).where(
        Measurement.device_id == device_id,
        Measurement.received_at >= now - timedelta(hours=24),
        Measurement.received_at <= now,
    ))
    latest = db.scalar(select(Measurement).where(
        Measurement.device_id == device_id,
    ).order_by(Measurement.received_at.desc(), Measurement.id.desc()).limit(1))
    received_at = latest.received_at if latest else None
    if received_at is None:
        status = "sem_dados"
    elif received_at > now:
        status = "horario_inconsistente"
    elif (now - received_at).total_seconds() > max_age_seconds:
        status = "desatualizado"
    else:
        status = "atualizado"
    return {
        "database": "ok",
        "checked_at": now.isoformat(),
        "device_id": device_id,
        "status": status,
        "measurements_received_24h": count,
        "last_received_at": received_at.isoformat() if received_at else None,
        "max_age_seconds": max_age_seconds,
    }


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("O valor deve ser positivo")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", default="esp32-01")
    parser.add_argument("--max-age-seconds", type=positive_int, default=300)
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            report = check_history(db, args.device_id, datetime.now(timezone.utc), args.max_age_seconds)
        print(json.dumps(report, ensure_ascii=False))
    except SQLAlchemyError:
        # Database errors can contain credentials or connection strings.
        print(json.dumps({"database": "error", "status": "consulta_falhou"}))
        raise SystemExit(1) from None
    if report["status"] != "atualizado":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
