from sqlalchemy import func, select
from app.models import ForecastModel


def latest_model(db, device_id, target='soil_raw'):
    # Legacy soil artifacts have no target key; public experiments declare another target.
    stored_target = func.coalesce(ForecastModel.artifact['target'].as_string(), 'soil_raw')
    return db.scalar(select(ForecastModel).where(ForecastModel.device_id == device_id,
                     stored_target == target).order_by(ForecastModel.trained_at.desc(), ForecastModel.id.desc()).limit(1))
