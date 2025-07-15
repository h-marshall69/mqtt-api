from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SensorData(BaseModel):
    temperature: float
    humidity: float
    light: Optional[float] = None
    timestamp: datetime

class AlarmData(BaseModel):
    type: str  # "movimiento", "temperatura", etc.
    state: bool  # True=activada, False=desactivada
    timestamp: datetime

class ButtonData(BaseModel):
    state: bool
    timestamp: datetime

class RGBData(BaseModel):
    red: int
    green: int
    blue: int
    timestamp: datetime
