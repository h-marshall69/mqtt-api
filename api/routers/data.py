from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from database import (
    SessionLocal,
    DBPaciente,
    DBMedicionesData,
    DBAlertasData,
    DBPrediccionesData,
    DBRawMQTTData,
    DBIdentificador,
    get_paciente,
    get_paciente_by_identifier,
    create_paciente,
    get_mediciones_por_paciente,
    get_alertas_por_paciente,
    get_predicciones_por_paciente
)
from models.schemas import (
    # Identificador
    IdentificadorBase, IdentificadorCreate, Identificador,
    # Pacientes
    Paciente, PacienteCreate, PacienteUpdate, PacienteDetailed, PatientSummary,
    # Mediciones
    MedicionesData, MedicionesDataCreate, MedicionesDataUpdate, MedicionesDataDetailed,
    # Alertas
    AlertasData, AlertasDataCreate, AlertasDataUpdate, AlertasDataDetailed,
    # Predicciones
    PrediccionesData, PrediccionesDataCreate, PrediccionesDataUpdate, PrediccionesDataDetailed,
    # MQTT
    RawMQTTData, RawMQTTDataProcessed,
    # Utils
    SystemStats, MQTTAnalysis, ErrorResponse
)
from typing import List, Optional
from datetime import datetime, timedelta
import json
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["data"])



# === DEPENDENCY: Database Session ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === UTILIDADES ===
def parse_mqtt_payload(payload_str: str):
    """Parse payload JSON string to dict"""
    try:
        return json.loads(payload_str) if isinstance(payload_str, str) else payload_str
    except json.JSONDecodeError:
        return {"raw_payload": payload_str}


# === IDENTIFICADOR ENDPOINTS ===
@router.post("/pacientes/identificador/", 
             response_model=Identificador, 
             status_code=status.HTTP_201_CREATED)
def crear_identificador(
    identificador: IdentificadorCreate, 
    db: Session = Depends(get_db)
):
    """Crear un nuevo identificador"""
    db_identificador = DBIdentificador(**identificador.dict())
    db.add(db_identificador)
    db.commit()
    db.refresh(db_identificador)
    return db_identificador

@router.get("/pacientes/identificador/", 
            response_model=Identificador)
def obtener_ultimo_identificador(
    db: Session = Depends(get_db)
):
    """Obtener el último identificador creado"""
    ultimo = db.query(DBIdentificador).order_by(DBIdentificador.id.desc()).first()
    if not ultimo:
        raise HTTPException(
            status_code=404, 
            detail="No se encontraron identificadores registrados"
        )
    return ultimo

# === PACIENTES ENDPOINTS ===
@router.get("/pacientes/", response_model=List[PacienteDetailed])
def listar_pacientes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Buscar por nombre o identificador")
):
    """Listar todos los pacientes con estadísticas básicas"""
    query = db.query(DBPaciente)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (DBPaciente.nombre.ilike(search_filter)) |
            (DBPaciente.identificador.ilike(search_filter))
        )
    
    pacientes = query.offset(skip).limit(limit).all()
    
    # Agregar estadísticas para cada paciente
    result = []
    for paciente in pacientes:
        stats = {
            "id": paciente.id,
            "identificador": paciente.identificador,
            "nombre": paciente.nombre,
            "fecha_registro": paciente.fecha_registro,
            "total_mediciones": db.query(DBMedicionesData).filter(DBMedicionesData.paciente_id == paciente.id).count(),
            "total_alertas": db.query(DBAlertasData).filter(DBAlertasData.paciente_id == paciente.id).count(),
            "total_predicciones": db.query(DBPrediccionesData).filter(DBPrediccionesData.paciente_id == paciente.id).count(),
            "ultima_medicion": db.query(DBMedicionesData.timestamp)
                              .filter(DBMedicionesData.paciente_id == paciente.id)
                              .order_by(DBMedicionesData.timestamp.desc())
                              .first()
        }
        result.append(stats)
    
    return result

@router.get("/pacientes/{paciente_id}", response_model=PatientSummary)
def obtener_paciente(paciente_id: int, db: Session = Depends(get_db)):
    """Obtener información detallada de un paciente"""
    paciente = get_paciente(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Obtener última medición, alerta y predicción
    ultima_medicion = db.query(DBMedicionesData)\
                       .filter(DBMedicionesData.paciente_id == paciente_id)\
                       .order_by(DBMedicionesData.timestamp.desc())\
                       .first()
    
    ultima_alerta = db.query(DBAlertasData)\
                     .filter(DBAlertasData.paciente_id == paciente_id)\
                     .order_by(DBAlertasData.timestamp.desc())\
                     .first()
    
    ultima_prediccion = db.query(DBPrediccionesData)\
                         .filter(DBPrediccionesData.paciente_id == paciente_id)\
                         .order_by(DBPrediccionesData.timestamp.desc())\
                         .first()
    
    # Contar alertas y mediciones en las últimas 24 horas
    last_24h = datetime.utcnow() - timedelta(hours=24)
    alertas_activas = db.query(DBAlertasData)\
                       .filter(DBAlertasData.paciente_id == paciente_id)\
                       .filter(DBAlertasData.timestamp >= last_24h)\
                       .count()
    
    mediciones_24h = db.query(DBMedicionesData)\
                      .filter(DBMedicionesData.paciente_id == paciente_id)\
                      .filter(DBMedicionesData.timestamp >= last_24h)\
                      .count()
    
    return {
        "paciente": paciente,
        "ultima_medicion": ultima_medicion,
        "ultima_alerta": ultima_alerta,
        "ultima_prediccion": ultima_prediccion,
        "alertas_activas": alertas_activas,
        "mediciones_24h": mediciones_24h
    }

@router.post("/pacientes/", response_model=Paciente, status_code=status.HTTP_201_CREATED)
def crear_paciente(paciente: PacienteCreate, db: Session = Depends(get_db)):
    """Crear un nuevo paciente"""
    # Verificar que no existe un paciente con el mismo identificador
    existing = get_paciente_by_identifier(paciente.identificador)
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un paciente con el identificador {paciente.identificador}"
        )
    
    try:
        db_paciente = create_paciente(paciente.dict())
        return db_paciente
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creando paciente: {str(e)}")

@router.put("/pacientes/{paciente_id}", response_model=Paciente)
def actualizar_paciente(
    paciente_id: int, 
    paciente_update: PacienteUpdate, 
    db: Session = Depends(get_db)
):
    """Actualizar información de un paciente"""
    db_paciente = get_paciente(paciente_id)
    if not db_paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    update_data = paciente_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_paciente, field, value)
    
    db = SessionLocal()
    try:
        db.add(db_paciente)
        db.commit()
        db.refresh(db_paciente)
        return db_paciente
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando paciente: {str(e)}")
    finally:
        db.close()

# === MEDICIONES ENDPOINTS ===
@router.get("/mediciones/", response_model=List[MedicionesDataDetailed])
def listar_mediciones(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    paciente_identificador: Optional[str] = Query(None),
    sensor: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    finger_detected: Optional[bool] = Query(None)
):
    """Listar mediciones con filtros opcionales"""
    query = db.query(DBMedicionesData).join(DBPaciente)
    
    # Aplicar filtros
    if paciente_identificador:
        query = query.filter(DBMedicionesData.paciente_identificador == paciente_identificador)
    if sensor:
        query = query.filter(DBMedicionesData.sensor.ilike(f"%{sensor}%"))
    if start_date:
        query = query.filter(DBMedicionesData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBMedicionesData.timestamp <= end_date)
    if finger_detected is not None:
        query = query.filter(DBMedicionesData.finger_detected == finger_detected)
    
    mediciones = query.order_by(DBMedicionesData.timestamp.desc()).offset(skip).limit(limit).all() 
        
    # Preparar respuesta
    result = []
    for medicion in mediciones:
        # Aplicar validaciones
        hr = medicion.heart_rate if medicion.heart_rate and 30 <= medicion.heart_rate <= 250 else None
        spo2 = medicion.spo2 if medicion.spo2 and 70 <= medicion.spo2 <= 100 else None
        temp = medicion.temperature if medicion.temperature and 30 <= medicion.temperature <= 45 else None
        
        medicion_dict = {
            "id": medicion.id,
            "paciente_identificador": medicion.paciente_identificador,
            "paciente_id": medicion.paciente.id if medicion.paciente else None,
            "sensor": medicion.sensor,
            "heart_rate": hr,
            "spo2": spo2,
            "temperature": temp,
            "finger_detected": medicion.finger_detected,
            "timestamp": medicion.timestamp,
            "paciente": medicion.paciente
        }
        result.append(medicion_dict)
    
    return result


@router.get("/pacientes/{paciente_id}/mediciones/", response_model=List[MedicionesData])
def obtener_mediciones_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500)
):
    """Obtener mediciones de un paciente específico"""
    paciente = get_paciente(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return get_mediciones_por_paciente(paciente_id, limit)

@router.get("/mediciones/latest/", response_model=List[MedicionesDataDetailed])
def obtener_ultimas_mediciones(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100)
):
    """Obtener las últimas mediciones del sistema"""
    mediciones = db.query(DBMedicionesData)\
                  .join(DBPaciente)\
                  .order_by(DBMedicionesData.timestamp.desc())\
                  .limit(limit)\
                  .all()
    
    result = []
    for medicion in mediciones:
        medicion_dict = {
            "id": medicion.id,
            "paciente_id": medicion.paciente_id,
            "sensor": medicion.sensor,
            "heart_rate": medicion.heart_rate,
            "spo2": medicion.spo2,
            "temperature": medicion.temperature,
            "finger_detected": medicion.finger_detected,
            "timestamp": medicion.timestamp,
            "paciente": medicion.paciente
        }
        result.append(medicion_dict)
    
    return result

# === ALERTAS ENDPOINTS ===
@router.get("/alertas/", response_model=List[AlertasDataDetailed])
def listar_alertas(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    paciente_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Listar alertas con filtros opcionales"""
    query = db.query(DBAlertasData).join(DBPaciente)
    
    # Aplicar filtros
    if paciente_id:
        query = query.filter(DBAlertasData.paciente_id == paciente_id)
    if tipo:
        query = query.filter(DBAlertasData.tipo.ilike(f"%{tipo}%"))
    if start_date:
        query = query.filter(DBAlertasData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBAlertasData.timestamp <= end_date)
    
    alertas = query.order_by(DBAlertasData.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Incluir información del paciente
    result = []
    for alerta in alertas:
        alerta_dict = {
            "id": alerta.id,
            "paciente_id": alerta.paciente_id,
            "tipo": alerta.tipo,
            "mensaje": alerta.mensaje,
            "timestamp": alerta.timestamp,
            "paciente": alerta.paciente
        }
        result.append(alerta_dict)
    
    return result

@router.get("/pacientes/{paciente_id}/alertas/", response_model=List[AlertasData])
def obtener_alertas_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500)
):
    """Obtener alertas de un paciente específico"""
    paciente = get_paciente(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return get_alertas_por_paciente(paciente_id, limit)

# === PREDICCIONES ENDPOINTS ===
@router.get("/predicciones/", response_model=List[PrediccionesDataDetailed])
def listar_predicciones(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    paciente_id: Optional[int] = Query(None),
    enfermedad: Optional[str] = Query(None),
    min_probabilidad: Optional[float] = Query(None, ge=0.0, le=1.0),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Listar predicciones con filtros opcionales"""
    query = db.query(DBPrediccionesData).join(DBPaciente)
    
    # Aplicar filtros
    if paciente_id:
        query = query.filter(DBPrediccionesData.paciente_id == paciente_id)
    if enfermedad:
        query = query.filter(DBPrediccionesData.enfermedad.ilike(f"%{enfermedad}%"))
    if min_probabilidad:
        query = query.filter(DBPrediccionesData.probabilidad >= min_probabilidad)
    if start_date:
        query = query.filter(DBPrediccionesData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBPrediccionesData.timestamp <= end_date)
    
    predicciones = query.order_by(DBPrediccionesData.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Incluir información del paciente
    result = []
    for prediccion in predicciones:
        prediccion_dict = {
            "id": prediccion.id,
            "paciente_id": prediccion.paciente_id,
            "enfermedad": prediccion.enfermedad,
            "heart_rate": prediccion.heart_rate,
            "probabilidad": prediccion.probabilidad,
            "timestamp": prediccion.timestamp,
            "paciente": prediccion.paciente
        }
        result.append(prediccion_dict)
    
    return result

@router.get("/pacientes/{paciente_id}/predicciones/", response_model=List[PrediccionesData])
def obtener_predicciones_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500)
):
    """Obtener predicciones de un paciente específico"""
    paciente = get_paciente(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    return get_predicciones_por_paciente(paciente_id, limit)

# === MQTT ENDPOINTS ===
@router.get("/mqtt/raw/", response_model=List[RawMQTTDataProcessed])
def obtener_datos_mqtt_crudos(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    topic: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None)
):
    """Obtener datos MQTT crudos con filtros"""
    query = db.query(DBRawMQTTData)
    
    # Aplicar filtros
    if topic:
        query = query.filter(DBRawMQTTData.topic.contains(topic))
    if start_date:
        query = query.filter(DBRawMQTTData.timestamp >= start_date)
    if end_date:
        query = query.filter(DBRawMQTTData.timestamp <= end_date)
    if search:
        query = query.filter(DBRawMQTTData.payload.contains(search))
    
    results = query.order_by(DBRawMQTTData.timestamp.desc()).offset(skip).limit(limit).all()
    
    # Procesar payloads
    processed_results = []
    for item in results:
        processed_results.append({
            "id": item.id,
            "topic": item.topic,
            "payload": parse_mqtt_payload(item.payload),
            "timestamp": item.timestamp
        })
    
    return processed_results

@router.get("/mqtt/topics/{topic}/", response_model=List[RawMQTTDataProcessed])
def obtener_datos_por_topic(
    topic: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200)
):
    """Obtener últimos mensajes de un topic específico"""
    results = db.query(DBRawMQTTData)\
               .filter(DBRawMQTTData.topic == topic)\
               .order_by(DBRawMQTTData.timestamp.desc())\
               .limit(limit)\
               .all()
    
    return [{
        "id": item.id,
        "topic": item.topic,
        "payload": parse_mqtt_payload(item.payload),
        "timestamp": item.timestamp
    } for item in results]

# === ESTADÍSTICAS ENDPOINTS ===
@router.get("/stats/", response_model=SystemStats)
def obtener_estadisticas_sistema(db: Session = Depends(get_db)):
    """Obtener estadísticas generales del sistema médico"""
    # Contar entidades
    total_pacientes = db.query(DBPaciente).count()
    total_mediciones = db.query(DBMedicionesData).count()
    total_alertas = db.query(DBAlertasData).count()
    total_predicciones = db.query(DBPrediccionesData).count()
    total_raw_mqtt = db.query(DBRawMQTTData).count()
    
    # Pacientes activos en las últimas 24 horas
    last_24h = datetime.utcnow() - timedelta(hours=24)
    pacientes_activos = db.query(DBPaciente.id)\
                         .join(DBMedicionesData)\
                         .filter(DBMedicionesData.timestamp >= last_24h)\
                         .distinct()\
                         .count()
    
    # Últimas actividades
    ultima_medicion = db.query(DBMedicionesData.timestamp)\
                       .order_by(DBMedicionesData.timestamp.desc())\
                       .first()
    
    ultima_alerta = db.query(DBAlertasData.timestamp)\
                     .order_by(DBAlertasData.timestamp.desc())\
                     .first()
    
    return {
        "total_pacientes": total_pacientes,
        "total_mediciones": total_mediciones,
        "total_alertas": total_alertas,
        "total_predicciones": total_predicciones,
        "total_raw_mqtt": total_raw_mqtt,
        "pacientes_activos_24h": pacientes_activos,
        "ultima_medicion": ultima_medicion[0] if ultima_medicion else None,
        "ultima_alerta": ultima_alerta[0] if ultima_alerta else None
    }

@router.get("/mqtt/analysis/", response_model=MQTTAnalysis)
def obtener_analisis_mqtt(db: Session = Depends(get_db)):
    """Análisis de patrones en los datos MQTT"""
    
    # Contar mensajes por topic
    from sqlalchemy import func
    topics_stats = db.query(
        DBRawMQTTData.topic,
        func.count(DBRawMQTTData.id).label('count')
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
def obtener_topics_desconocidos(db: Session = Depends(get_db)):
    """Encuentra topics que no están siendo procesados específicamente"""
    
    # Topics conocidos del sistema médico
    known_topics = [
        "medical/mediciones", 
        "medical/alertas", 
        "medical/predicciones",
        "esp32/sensors",  # Mantener compatibilidad con versión anterior
        "esp32/alarms",
        "system/health"
    ]
    
    unknown = db.query(DBRawMQTTData.topic)\
               .filter(~DBRawMQTTData.topic.in_(known_topics))\
               .distinct()\
               .all()
    
    return {
        "unknown_topics": [t[0] for t in unknown],
        "known_topics": known_topics,
        "suggestion": "Considere agregar manejadores específicos para estos topics"
    }

# === ENDPOINTS DE ANÁLISIS Y REPORTES ===
@router.get("/reportes/paciente/{paciente_id}/resumen-medico/")
def obtener_resumen_medico_paciente(
    paciente_id: int,
    db: Session = Depends(get_db),
    dias: int = Query(7, ge=1, le=90, description="Número de días hacia atrás para el reporte")
):
    """Generar resumen médico completo de un paciente"""
    paciente = get_paciente(paciente_id)
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    # Fecha de inicio para el reporte
    start_date = datetime.utcnow() - timedelta(days=dias)
    
    # Obtener datos del período
    mediciones = db.query(DBMedicionesData)\
                  .filter(DBMedicionesData.paciente_id == paciente_id)\
                  .filter(DBMedicionesData.timestamp >= start_date)\
                  .order_by(DBMedicionesData.timestamp.desc())\
                  .all()
    
    alertas = db.query(DBAlertasData)\
               .filter(DBAlertasData.paciente_id == paciente_id)\
               .filter(DBAlertasData.timestamp >= start_date)\
               .order_by(DBAlertasData.timestamp.desc())\
               .all()
    
    predicciones = db.query(DBPrediccionesData)\
                    .filter(DBPrediccionesData.paciente_id == paciente_id)\
                    .filter(DBPrediccionesData.timestamp >= start_date)\
                    .order_by(DBPrediccionesData.timestamp.desc())\
                    .all()
    
    # Calcular estadísticas
    if mediciones:
        heart_rates = [m.heart_rate for m in mediciones if m.heart_rate]
        spo2_values = [m.spo2 for m in mediciones if m.spo2]
        temperatures = [m.temperature for m in mediciones if m.temperature]
        
        stats_mediciones = {
            "total_mediciones": len(mediciones),
            "heart_rate": {
                "promedio": sum(heart_rates) / len(heart_rates) if heart_rates else None,
                "minimo": min(heart_rates) if heart_rates else None,
                "maximo": max(heart_rates) if heart_rates else None
            },
            "spo2": {
                "promedio": sum(spo2_values) / len(spo2_values) if spo2_values else None,
                "minimo": min(spo2_values) if spo2_values else None,
                "maximo": max(spo2_values) if spo2_values else None
            },
            "temperature": {
                "promedio": sum(temperatures) / len(temperatures) if temperatures else None,
                "minimo": min(temperatures) if temperatures else None,
                "maximo": max(temperatures) if temperatures else None
            }
        }
    else:
        stats_mediciones = {"total_mediciones": 0}
    
    # Agrupar alertas por tipo
    alertas_por_tipo = {}
    for alerta in alertas:
        if alerta.tipo not in alertas_por_tipo:
            alertas_por_tipo[alerta.tipo] = 0
        alertas_por_tipo[alerta.tipo] += 1
    
    # Agrupar predicciones por enfermedad
    predicciones_por_enfermedad = {}
    for prediccion in predicciones:
        if prediccion.enfermedad not in predicciones_por_enfermedad:
            predicciones_por_enfermedad[prediccion.enfermedad] = []
        predicciones_por_enfermedad[prediccion.enfermedad].append(prediccion.probabilidad)
    
    # Calcular promedio de probabilidades por enfermedad
    predicciones_promedio = {}
    for enfermedad, probabilidades in predicciones_por_enfermedad.items():
        predicciones_promedio[enfermedad] = {
            "probabilidad_promedio": sum(probabilidades) / len(probabilidades),
            "total_predicciones": len(probabilidades),
            "probabilidad_maxima": max(probabilidades)
        }
    
    return {
        "paciente": paciente,
        "periodo": {
            "inicio": start_date.isoformat(),
            "fin": datetime.utcnow().isoformat(),
            "dias": dias
        },
        "estadisticas_mediciones": stats_mediciones,
        "total_alertas": len(alertas),
        "alertas_por_tipo": alertas_por_tipo,
        "total_predicciones": len(predicciones),
        "predicciones_por_enfermedad": predicciones_promedio,
        "alertas_recientes": [
            {
                "tipo": a.tipo,
                "mensaje": a.mensaje,
                "timestamp": a.timestamp.isoformat()
            } for a in alertas[:5]  # Últimas 5 alertas
        ]
    }

@router.get("/dashboard/")
def obtener_dashboard():
    """Endpoint para dashboard principal con KPIs"""
    db = SessionLocal()
    try:
        # KPIs principales
        total_pacientes = db.query(DBPaciente).count()
        
        # Actividad últimas 24 horas
        last_24h = datetime.utcnow() - timedelta(hours=24)
        mediciones_24h = db.query(DBMedicionesData)\
                          .filter(DBMedicionesData.timestamp >= last_24h)\
                          .count()
        
        alertas_24h = db.query(DBAlertasData)\
                       .filter(DBAlertasData.timestamp >= last_24h)\
                       .count()
        
        # Pacientes con actividad reciente
        pacientes_activos = db.query(DBPaciente.id)\
                             .join(DBMedicionesData)\
                             .filter(DBMedicionesData.timestamp >= last_24h)\
                             .distinct()\
                             .count()
        
        # Alertas críticas (últimas 2 horas)
        last_2h = datetime.utcnow() - timedelta(hours=2)
        alertas_criticas = db.query(DBAlertasData)\
                            .filter(DBAlertasData.timestamp >= last_2h)\
                            .filter(DBAlertasData.tipo.in_(['heart_rate_critical', 'spo2_critical', 'temperature_critical']))\
                            .count()
        
        # Top 5 pacientes con más alertas en 24h
        from sqlalchemy import func
        top_pacientes_alertas = db.query(
            DBPaciente.nombre,
            DBPaciente.identificador,
            func.count(DBAlertasData.id).label('total_alertas')
        ).join(DBAlertasData)\
         .filter(DBAlertasData.timestamp >= last_24h)\
         .group_by(DBPaciente.id, DBPaciente.nombre, DBPaciente.identificador)\
         .order_by(func.count(DBAlertasData.id).desc())\
         .limit(5)\
         .all()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "kpis": {
                "total_pacientes": total_pacientes,
                "pacientes_activos_24h": pacientes_activos,
                "mediciones_24h": mediciones_24h,
                "alertas_24h": alertas_24h,
                "alertas_criticas_2h": alertas_criticas
            },
            "top_pacientes_alertas": [
                {
                    "nombre": p.nombre,
                    "identificador": p.identificador,
                    "total_alertas": p.total_alertas
                } for p in top_pacientes_alertas
            ]
        }
    finally:
        db.close()

# === ENDPOINTS DE BÚSQUEDA ===
@router.get("/buscar/")
def buscar_en_sistema(
    q: str = Query(..., min_length=2, description="Término de búsqueda"),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """Búsqueda global en el sistema médico"""
    search_term = f"%{q}%"
    
    # Buscar pacientes
    pacientes = db.query(DBPaciente)\
                 .filter(
                     (DBPaciente.nombre.ilike(search_term)) |
                     (DBPaciente.identificador.ilike(search_term))
                 )\
                 .limit(limit)\
                 .all()
    
    # Buscar en alertas
    alertas = db.query(DBAlertasData)\
               .join(DBPaciente)\
               .filter(
                   (DBAlertasData.tipo.ilike(search_term)) |
                   (DBAlertasData.mensaje.ilike(search_term)) |
                   (DBPaciente.nombre.ilike(search_term))
               )\
               .limit(limit)\
               .all()
    
    # Buscar en predicciones
    predicciones = db.query(DBPrediccionesData)\
                    .join(DBPaciente)\
                    .filter(
                        (DBPrediccionesData.enfermedad.ilike(search_term)) |
                        (DBPaciente.nombre.ilike(search_term))
                    )\
                    .limit(limit)\
                    .all()
    
    return {
        "query": q,
        "resultados": {
            "pacientes": [
                {
                    "id": p.id,
                    "nombre": p.nombre,
                    "identificador": p.identificador,
                    "tipo": "paciente"
                } for p in pacientes
            ],
            "alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo,
                    "mensaje": a.mensaje,
                    "paciente": a.paciente.nombre,
                    "timestamp": a.timestamp.isoformat(),
                    "tipo": "alerta"
                } for a in alertas
            ],
            "predicciones": [
                {
                    "id": p.id,
                    "enfermedad": p.enfermedad,
                    "probabilidad": p.probabilidad,
                    "paciente": p.paciente.nombre,
                    "timestamp": p.timestamp.isoformat(),
                    "tipo": "prediccion"
                } for p in predicciones
            ]
        },
        "total_resultados": len(pacientes) + len(alertas) + len(predicciones)
    }
