"""Train an evaluated model from the real device history in the configured DB."""
import argparse
from datetime import datetime, timezone
import json
from uuid import uuid4

from sqlalchemy import select
from app.database import SessionLocal
from app.models import ForecastModel, Measurement
from app.forecasting import fit_model, InsufficientData


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--limit", type=int, default=100000)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000000:
        parser.error("limit deve estar entre 1 e 1000000")
    with SessionLocal() as db:
        rows = db.scalars(select(Measurement).where(Measurement.device_id == args.device_id)
                          .order_by(Measurement.measured_at.desc(), Measurement.id.desc())
                          .limit(args.limit)).all()
        try:
            artifact = fit_model(rows, datetime.now(timezone.utc))
        except InsufficientData as exc:
            parser.exit(2, f"Treino não realizado: {exc}\n")
        artifact["source_rows"] = len(rows)
        artifact["source_limit"] = args.limit
        artifact["source_limit_reached"] = len(rows) == args.limit
        model = ForecastModel(id=str(uuid4()), device_id=args.device_id, artifact=artifact)
        db.add(model)
        db.commit()
        print(json.dumps({"model_id": model.id, **artifact}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
