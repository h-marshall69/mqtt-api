from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
import json

# === SCHEMAS BASE ===
class BaseTimestamp(BaseModel):
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# === PACIENTE SCHEMAS ===
class PacienteBase(BaseModel):
    identificador: str = Field(..., description="Identificador único del paciente (DNI, código, etc.)")
    nombre: str = Field(..., description="Nombre completo del paciente")

class PacienteCreate(PacienteBase):
    pass

class PacienteUpdate(BaseModel):
    nombre: Optional[str] = None

class Paciente(PacienteBase):
    id: int
    fecha_registro: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PacienteDetailed(Paciente):
    """Paciente con información relacionada"""
    total_mediciones: Optional[int] = 0
    total_alertas: Optional[int] = 0
    total_predicciones: Optional[int] = 0
    ultima_medicion: Optional[datetime] = None

# === IDENTIFICADOR SCHEMAS ===
class IdentificadorBase(BaseModel):
    identificador: str

class IdentificadorCreate(IdentificadorBase):
    pass

class Identificador(IdentificadorBase):
    id: int
    
    class Config:
        from_attributes = True

# === MEDICIONES SCHEMAS ===
class MedicionesDataBase(BaseModel):
    sensor: Optional[str] = None
    heart_rate: Optional[int] = Field(None, ge=0, le=300, description="Frecuencia cardíaca en BPM")
    spo2: Optional[int] = Field(None, ge=0, le=100, description="Saturación de oxígeno en %")
    temperature: Optional[float] = Field(None, ge=30.0, le=45.0, description="Temperatura corporal en °C")
    finger_detected: Optional[bool] = Field(False, description="Detección de dedo en el sensor")

    @validator('heart_rate')
    def validate_heart_rate(cls, v):
        if v is not None and (v < 30 or v > 250):
            raise ValueError('Frecuencia cardíaca fuera de rango normal (30-250 BPM)')
        return v

    @validator('spo2')
    def validate_spo2(cls, v):
        if v is not None and (v < 70 or v > 100):
            raise ValueError('SpO2 fuera de rango válido (70-100%)')
        return v

class MedicionesDataCreate(MedicionesDataBase):
    paciente_identificador: str
    timestamp: Optional[datetime] = None

class MedicionesDataUpdate(BaseModel):
    sensor: Optional[str] = None
    heart_rate: Optional[int] = None
    spo2: Optional[int] = None
    temperature: Optional[float] = None
    finger_detected: Optional[bool] = None

class MedicionesData(MedicionesDataBase, BaseTimestamp):
    id: int

    paciente_id: Optional[int] = None  # Para compatibilidad con otras tablas
    paciente_identificador: str  # Para coincidir con la DB
    
    class Config:
        from_attributes = True
        fields = {
            'paciente_identificador': {'alias': 'paciente.identificador'}
        }

class MedicionesDataDetailed(MedicionesData):
    """Medición con información del paciente"""
    paciente: Optional[Paciente] = None


# === ALERTAS SCHEMAS ===
class AlertasDataBase(BaseModel):
    tipo: str = Field(..., description="Tipo de alerta (ej: heart_rate_high, spo2_low, temperature_high)")
    mensaje: str = Field(..., description="Mensaje descriptivo de la alerta")

class AlertasDataCreate(AlertasDataBase):
    paciente_id: int
    timestamp: Optional[datetime] = None

class AlertasDataUpdate(BaseModel):
    tipo: Optional[str] = None
    mensaje: Optional[str] = None

class AlertasData(AlertasDataBase, BaseTimestamp):
    id: int
    paciente_id: int
    
    class Config:
        from_attributes = True

class AlertasDataDetailed(AlertasData):
    """Alerta con información del paciente"""
    paciente: Optional[Paciente] = None


# === PREDICCIONES SCHEMAS ===
class PrediccionesDataBase(BaseModel):
    enfermedad: str = Field(..., description="Nombre de la enfermedad predicha")
    heart_rate: Optional[int] = Field(None, description="Frecuencia cardíaca usada para la predicción")
    probabilidad: float = Field(..., ge=0.0, le=1.0, description="Probabilidad de la predicción (0.0 - 1.0)")

    @validator('probabilidad')
    def validate_probabilidad(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('La probabilidad debe estar entre 0.0 y 1.0')
        return v

class PrediccionesDataCreate(PrediccionesDataBase):
    paciente_id: int
    timestamp: Optional[datetime] = None

class PrediccionesDataUpdate(BaseModel):
    enfermedad: Optional[str] = None
    heart_rate: Optional[int] = None
    probabilidad: Optional[float] = None

class PrediccionesData(PrediccionesDataBase, BaseTimestamp):
    id: int
    paciente_id: int
    
    class Config:
        from_attributes = True

class PrediccionesDataDetailed(PrediccionesData):
    """Predicción con información del paciente"""
    paciente: Optional[Paciente] = None

# === RAW MQTT SCHEMAS ===
class RawMQTTDataBase(BaseModel):
    topic: str
    payload: str = Field(..., description="Payload como string JSON")

class RawMQTTDataCreate(RawMQTTDataBase):
    timestamp: Optional[datetime] = None

class RawMQTTData(RawMQTTDataBase, BaseTimestamp):
    id: int
    
    class Config:
        from_attributes = True

class RawMQTTDataProcessed(BaseModel):
    """MQTT Data with parsed payload"""
    id: int
    topic: str
    payload: dict  # Payload parseado como dict
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# === RESPONSE SCHEMAS ===
class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    total: int
    page: int
    size: int
    pages: int
    items: List[dict]

class SystemStats(BaseModel):
    """Estadísticas del sistema médico"""
    total_pacientes: int
    total_mediciones: int
    total_alertas: int
    total_predicciones: int
    total_raw_mqtt: int
    pacientes_activos_24h: int
    ultima_medicion: Optional[datetime] = None
    ultima_alerta: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MQTTAnalysis(BaseModel):
    """Análisis de datos MQTT"""
    total_messages: int
    unique_topics: List[str]
    messages_by_topic: dict
    last_24h_messages: int
    most_active_topic: Optional[str] = None

class PatientSummary(BaseModel):
    """Resumen de un paciente con últimos datos"""
    paciente: Paciente
    ultima_medicion: Optional[MedicionesData] = None
    ultima_alerta: Optional[AlertasData] = None
    ultima_prediccion: Optional[PrediccionesData] = None
    alertas_activas: int
    mediciones_24h: int

# === FILTER SCHEMAS ===
class DateRangeFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=500)

class MedicionesFilter(DateRangeFilter, PaginationParams):
    paciente_id: Optional[int] = None
    sensor: Optional[str] = None
    min_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    min_spo2: Optional[int] = None
    max_spo2: Optional[int] = None
    finger_detected: Optional[bool] = None

class AlertasFilter(DateRangeFilter, PaginationParams):
    paciente_id: Optional[int] = None
    tipo: Optional[str] = None

class PrediccionesFilter(DateRangeFilter, PaginationParams):
    paciente_id: Optional[int] = None
    enfermedad: Optional[str] = None
    min_probabilidad: Optional[float] = Field(None, ge=0.0, le=1.0)

# === ERROR SCHEMAS ===
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
