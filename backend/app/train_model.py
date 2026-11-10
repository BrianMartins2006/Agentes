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
    parser.add_argument("--target", choices=("soil_raw","temperature_c"), default="soil_raw")
    parser.add_argument("--report", type=str, help="Salvar metadados e métricas JSON, sem árvores")
    parser.add_argument("--as-of", help="Instante UTC/com fuso usado para encerrar os minutos completos")
    parser.add_argument("--max-id", type=int, help="Reproduzir um corte histórico sem incluir novas medições")
    parser.add_argument("--limit", type=int, default=100000)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000000:
        parser.error("limit deve estar entre 1 e 1000000")
    now = datetime.now(timezone.utc)
    if args.as_of:
        try:
            now = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
            if now.tzinfo is None:
                parser.error("as-of deve incluir fuso horário")
        except ValueError:
            parser.error("as-of deve ser data ISO 8601 com fuso")
    with SessionLocal() as db:
        query = select(Measurement).where(Measurement.device_id == args.device_id)
        if args.max_id is not None:
            query = query.where(Measurement.id <= args.max_id)
        rows = db.scalars(query.order_by(Measurement.measured_at.desc(), Measurement.id.desc())
                          .limit(args.limit)).all()
        try:
            artifact = fit_model(rows, now, args.target)
        except InsufficientData as exc:
            parser.exit(2, f"Treino não realizado: {exc}\n")
        artifact["source_max_id"] = max(row.id for row in rows)
        artifact["source_rows"] = len(rows)
        artifact["source_limit"] = args.limit
        artifact["source_limit_reached"] = len(rows) == args.limit
        model = ForecastModel(id=str(uuid4()), device_id=args.device_id, artifact=artifact)
        db.add(model)
        db.commit()
        report = {"model_id": model.id, "device_id":args.device_id,
                  **{key:value for key,value in artifact.items() if key != "trees"}}
        if args.report:
            from pathlib import Path
            path=Path(args.report);path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
