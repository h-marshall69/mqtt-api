from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import (
    SessionLocal,
    DBSensorData,
    DBAlarmData,
    DBButtonData,
    DBRGBData
)
from models.schemas import (
    SensorData,
    AlarmData,
    ButtonData,
    RGBData
)
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1", tags=["data"])

# --- Dependency: sesión de base de datos ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Filtros comunes ---
async def common_filters(
    skip: int = 0,
    limit: int = Query(100, le=500),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    return {
        "skip": skip,
        "limit": limit,
        "start_date": start_date,
        "end_date": end_date
    }

# --- Endpoint: Sensor Data ---
@router.get("/sensors/", response_model=List[SensorData])
def read_sensor_data(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, le=500),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    query = db.query(DBSensorData)
    
    if start_date:
        query = query.filter(DBSensorData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBSensorData.timestamp <= end_date)
    
    return query.order_by(DBSensorData.timestamp.desc()).offset(skip).limit(limit).all()

# --- Endpoint: Alarm Data ---
@router.get("/alarms/", response_model=List[AlarmData])
def read_alarm_data(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, le=500),
    alarm_type: Optional[str] = None,
    state: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    query = db.query(DBAlarmData)
    
    if alarm_type:
        query = query.filter(DBAlarmData.type == alarm_type)
    if state is not None:
        query = query.filter(DBAlarmData.state == state)
    if start_date:
        query = query.filter(DBAlarmData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBAlarmData.timestamp <= end_date)
    
    return query.order_by(DBAlarmData.timestamp.desc()).offset(skip).limit(limit).all()

# --- Endpoint: Latest Sensor Data ---
@router.get("/sensors/latest/", response_model=SensorData)
def read_latest_sensor_data(db: Session = Depends(get_db)):
    latest = db.query(DBSensorData).order_by(DBSensorData.timestamp.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No sensor data found")
    return latest

# --- Endpoint: Button Data ---
@router.get("/button/", response_model=List[ButtonData])
def read_button_data(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, le=500),
    state: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    query = db.query(DBButtonData)
    
    if state is not None:
        query = query.filter(DBButtonData.state == state)
    if start_date:
        query = query.filter(DBButtonData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBButtonData.timestamp <= end_date)
    
    return query.order_by(DBButtonData.timestamp.desc()).offset(skip).limit(limit).all()

# --- Endpoint: RGB Data ---
@router.get("/rgb/", response_model=List[RGBData])
def read_rgb_data(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, le=500),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    query = db.query(DBRGBData)
    
    if start_date:
        query = query.filter(DBRGBData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBRGBData.timestamp <= end_date)
    
    return query.order_by(DBRGBData.timestamp.desc()).offset(skip).limit(limit).all()

# --- Endpoint: Stats ---
@router.get("/stats/")
def get_system_stats(db: Session = Depends(get_db)):
    """Endpoint para obtener estadísticas del sistema"""
    stats = {
        "sensor_data_count": db.query(DBSensorData).count(),
        "alarm_data_count": db.query(DBAlarmData).count(),
        "button_data_count": db.query(DBButtonData).count(),
        "rgb_data_count": db.query(DBRGBData).count(),
        "last_sensor_data": db.query(DBSensorData.timestamp)
                            .order_by(DBSensorData.timestamp.desc())
                            .first()[0] if db.query(DBSensorData).count() > 0 else None,
        "last_alarm": db.query(DBAlarmData.timestamp)
                      .order_by(DBAlarmData.timestamp.desc())
                      .first()[0] if db.query(DBAlarmData).count() > 0 else None
    }
    return stats
