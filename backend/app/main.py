from datetime import datetime, timedelta, timezone
from secrets import compare_digest
from typing import Annotated
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_session
from app.models import ForecastModel, Measurement
from app.forecasting import forecast, InsufficientData
from app.schemas import MeasurementCreate, MeasurementRead
from app.auto_train import training_loop

@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(training_loop()) if settings.ml_auto_train_enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(title="Monitoramento Ambiental IoT", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET"], allow_headers=["X-API-Key"], allow_credentials=False)
dashboard_path = Path(__file__).resolve().parents[2] / "dashboard" / "dist"
if (dashboard_path / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=dashboard_path / "assets"), name="dashboard-assets")
Db = Annotated[Session, Depends(get_session)]
key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@app.get("/", include_in_schema=False)
def dashboard():
    if (dashboard_path / "index.html").is_file():
        return FileResponse(dashboard_path / "index.html")
    return {"service": "Ambiente API", "docs": "/docs", "frontend": "React/Vite — execute npm run dev em dashboard/"}


def authenticate(key: Annotated[str | None, Security(key_header)]):
    expected = settings.ingest_api_key.get_secret_value()
    if not key or not expected or not compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Chave de API inválida")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/predictions", dependencies=[Depends(authenticate)])
def prediction(db: Db, device_id: str = Query(min_length=1, max_length=64)):
    model = db.scalar(select(ForecastModel).where(ForecastModel.device_id == device_id)
                      .order_by(ForecastModel.trained_at.desc(), ForecastModel.id.desc()).limit(1))
    if model is None:
        return {"status": "unavailable", "reason": "Modelo ainda não treinado; aguardando histórico suficiente",
                "device_id": device_id, "automatic_training": settings.ml_auto_train_enabled}
    now = datetime.now(timezone.utc)
    rows = db.scalars(select(Measurement).where(Measurement.device_id == device_id,
                      Measurement.measured_at >= now - timedelta(minutes=15),
                      Measurement.measured_at <= now)).all()
    try:
        result = forecast(model.artifact, rows, now)
    except InsufficientData as exc:
        result = {"status": "unavailable", "reason": str(exc)}
    return {"device_id": device_id, "model_id": model.id,
            "trained_at": model.trained_at, "automatic_training": settings.ml_auto_train_enabled, **result}


@app.post("/api/v1/measurements", response_model=MeasurementRead, status_code=201,
          dependencies=[Depends(authenticate)])
def create_measurement(payload: MeasurementCreate, db: Db):
    row = Measurement(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/v1/measurements", response_model=list[MeasurementRead],
         dependencies=[Depends(authenticate)])
def list_measurements(db: Db, device_id: str | None = None,
                      since: Annotated[datetime | None, Query()] = None,
                      until: Annotated[datetime | None, Query()] = None,
                      limit: int = Query(default=100, ge=1, le=1000),
                      offset: int = Query(default=0, ge=0)):
    query = select(Measurement)
    if until is not None:
        if until.tzinfo is None:
            raise HTTPException(status_code=422, detail="until deve incluir fuso horário")
        if since is not None and since.tzinfo is not None and since > until:
            raise HTTPException(status_code=422, detail="Início deve ser anterior ao fim")
        query = query.where(Measurement.measured_at <= until)
    if device_id is not None:
        query = query.where(Measurement.device_id == device_id)
    if since is not None:
        if since.tzinfo is None:
            raise HTTPException(status_code=422, detail="since deve incluir fuso horário")
        query = query.where(Measurement.measured_at >= since)
    return db.scalars(query.order_by(Measurement.measured_at.desc(), Measurement.id.desc())
                      .limit(limit).offset(offset)).all()
