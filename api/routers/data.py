from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from database import (
    SessionLocal,
    DBSensorData,
    DBAlarmData,
    DBButtonData,
    DBRGBData,
    DBRawMQTTData
)
from models.schemas import (
    SensorData,
    AlarmData,
    ButtonData,
    RGBData
)
from typing import List, Optional
from datetime import datetime, timedelta
import json
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["data"])

# Nuevo esquema para datos MQTT crudos
class RawMQTTData(BaseModel):
    id: int
    topic: str
    payload: dict  # o Any si puede ser de cualquier tipo
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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

# Nuevo endpoint para datos MQTT crudos
@router.get("/mqtt/raw/", response_model=List[RawMQTTData])
def read_raw_mqtt_data(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = Query(100, le=500),
    topic: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None
):
    query = db.query(DBRawMQTTData)
    
    # Filtros
    if topic:
        query = query.filter(DBRawMQTTData.topic.contains(topic))
    if start_date:
        query = query.filter(DBRawMQTTData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBRawMQTTData.timestamp <= end_date)
    if search:
        query = query.filter(DBRawMQTTData.payload.contains(search))
    
    results = query.order_by(DBRawMQTTData.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Procesar los payloads para convertirlos a dict
    processed_results = []
    for item in results:
        try:
            payload = json.loads(item.payload) if isinstance(item.payload, str) else item.payload
        except json.JSONDecodeError:
            payload = item.payload
            
        processed_results.append({
            "id": item.id,
            "topic": item.topic,
            "payload": payload,
            "timestamp": item.timestamp
        })
    
    return processed_results

# Nuevo endpoint para los últimos N mensajes de un topic específico
@router.get("/mqtt/topic/{topic}/", response_model=List[RawMQTTData])
def read_mqtt_topic_data(
    topic: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200)
):
    results = db.query(DBRawMQTTData)\
               .filter(DBRawMQTTData.topic == topic)\
               .order_by(DBRawMQTTData.timestamp.desc())\
               .limit(limit)\
               .all()
    
    return [{
        "id": item.id,
        "topic": item.topic,
        "payload": json.loads(item.payload) if isinstance(item.payload, str) else item.payload,
        "timestamp": item.timestamp
    } for item in results]

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

@router.get("/mqtt/analysis/")
def get_mqtt_analysis(db: Session = Depends(get_db)):
    """Análisis de patrones en los datos MQTT"""
    
    # Contar mensajes por topic
    topics_stats = db.query(
        DBRawMQTTData.topic,
        db.func.count(DBRawMQTTData.id).label('count')
    ).group_by(DBRawMQTTData.topic).all()
    
    # Últimos 24 horas de actividad
    last_24h = datetime.utcnow() - timedelta(hours=24)
    recent_activity = db.query(DBRawMQTTData)\
                       .filter(DBRawMQTTData.timestamp >= last_24h)\
                       .count()
    
    # Topics únicos
    unique_topics = db.query(DBRawMQTTData.topic).distinct().all()
    
    return {
        "total_messages": db.query(DBRawMQTTData).count(),
        "unique_topics": [t[0] for t in unique_topics],
        "messages_by_topic": {t.topic: t.count for t in topics_stats},
        "last_24h_messages": recent_activity,
        "most_active_topic": max(topics_stats, key=lambda x: x.count).topic if topics_stats else None
    }


@router.get("/mqtt/unknown-topics/")
def get_unknown_topics(db: Session = Depends(get_db)):
    """Encuentra topics que no están siendo procesados específicamente"""
    
    known_topics = ["esp32/sensors", "esp32/alarms", "esp32/button", "esp32/rgb"]
    
    unknown = db.query(DBRawMQTTData.topic)\
               .filter(~DBRawMQTTData.topic.in_(known_topics))\
               .distinct()\
               .all()
    
    return {
        "unknown_topics": [t[0] for t in unknown],
        "suggestion": "Consider adding specific handlers for these topics"
    }
