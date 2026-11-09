from datetime import datetime
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class MeasurementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    device_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    temperature_c: float
    air_humidity_pct: float = Field(ge=0, le=100)
    soil_raw: int = Field(ge=0, strict=True)
    measured_at: AwareDatetime


class MeasurementRead(MeasurementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    received_at: datetime
