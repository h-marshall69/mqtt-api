from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

SQLALCHEMY_DATABASE_URL = "sqlite:///./esp32_data.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Tabla: Identificador
class DBIdentificador(Base):
    __tablename__ = "identificador"
    
    id = Column(Integer, primary_key=True, index=True)
    identificador = Column(String)

# Tabla: Paciente
class DBPaciente(Base):
    __tablename__ = "pacientes"
    
    id = Column(Integer, primary_key=True, index=True)
    identificador = Column(String, unique=True, index=True)  # Puede ser DNI, código único, etc.
    nombre = Column(String, nullable=False)
    #apellido = Column(String, nullable=False)
    #edad = Column(Integer)
    #genero = Column(String)
    #telefono = Column(String)
    #email = Column(String)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    #notas_medicas = Column(String)
    
    # Relaciones
    mediciones = relationship("DBMedicionesData", back_populates="paciente")
    alertas = relationship("DBAlertasData", back_populates="paciente")
    predicciones = relationship("DBPrediccionesData", back_populates="paciente")

# Tabla: Datos de Mediciones
class DBMedicionesData(Base):
    __tablename__ = "mediciones_data"
    
    id = Column(Integer, primary_key=True, index=True)
    #paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    paciente_identificador = Column(String, ForeignKey('pacientes.identificador'))
    sensor = Column(String)
    heart_rate = Column(Integer)
    spo2 = Column(Integer)
    temperature = Column(Float)
    finger_detected = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relación
    paciente = relationship("DBPaciente", back_populates="mediciones")

# Tabla: Datos de Alertas
class DBAlertasData(Base):
    __tablename__ = "alertas_data"

    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    tipo = Column(String)  # Cambiado de Integer a String para más flexibilidad
    mensaje = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relación
    paciente = relationship("DBPaciente", back_populates="alertas")


# Tabla: Datos de Predicciones (corregido typo en Coluimn)
class DBPrediccionesData(Base):
    __tablename__ = "predicciones_data"
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'))
    enfermedad = Column(String)
    heart_rate = Column(Integer)
    probabilidad = Column(Float)  # Corregido typo
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relación
    paciente = relationship("DBPaciente", back_populates="predicciones")

# Tabla: Mensajes MQTT crudos
class DBRawMQTTData(Base):
    __tablename__ = "raw_mqtt_data"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String)
    payload = Column(String)  # Almacenamos como string JSON
    timestamp = Column(DateTime, default=datetime.utcnow)

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

# Funciones CRUD para Pacientes
def create_paciente(paciente_data: dict):
    db = SessionLocal()
    try:
        db_paciente = DBPaciente(
            identificador=paciente_data['identificador'],
            nombre=paciente_data['nombre'],
            #apellido=paciente_data['apellido'],
            #edad=paciente_data.get('edad'),
            #genero=paciente_data.get('genero'),
            #telefono=paciente_data.get('telefono'),
            #email=paciente_data.get('email'),
            #notas_medicas=paciente_data.get('notas_medicas')
        )
        db.add(db_paciente)
        db.commit()
        db.refresh(db_paciente)
        return db_paciente
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_paciente(paciente_id: int):
    db = SessionLocal()
    try:
        return db.query(DBPaciente).filter(DBPaciente.id == paciente_id).first()
    finally:
        db.close()

def get_paciente_by_identifier(identificador: str):
    db = SessionLocal()
    try:
        return db.query(DBPaciente).filter(DBPaciente.identificador == identificador).first()
    finally:
        db.close()

# Funciones de guardado de datos
def save_mediciones_data(data: dict):
    db = SessionLocal()
    try:
        # Validar que existe el paciente
        if 'paciente_identificador' not in data:
            raise ValueError("Se requiere paciente_identificador para guardar mediciones")
            
        db_data = DBMedicionesData(
            paciente_identificador=data['paciente_identificador'],
            sensor=data.get('sensor'),
            heart_rate=data.get('heart_rate'),
            spo2=data.get('spo2'),
            temperature=data.get('temperature'),
            finger_detected=data.get('finger_detected', False),
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp']
        )
        db.add(db_data)
        db.commit()
        raise ValueError("Lo logro senior")
        return db_data
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def save_alertas_data(data: dict):
    db = SessionLocal()
    try:
        if 'paciente_id' not in data:
            raise ValueError("Se requiere paciente_id para guardar alertas")
            
        db_data = DBAlertasData(
            paciente_id=data['paciente_id'],
            tipo=data.get('tipo'),
            mensaje=data.get('mensaje'),
            timestamp=data.get('timestamp', datetime.utcnow())
        )
        db.add(db_data)
        db.commit()
        return db_data
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def save_predicciones_data(data: dict):
    db = SessionLocal()
    try:
        if 'paciente_id' not in data:
            raise ValueError("Se requiere paciente_id para guardar predicciones")
            
        db_data = DBPrediccionesData(
            paciente_id=data['paciente_id'],
            enfermedad=data.get('enfermedad'),
            heart_rate=data.get('heart_rate'),
            probabilidad=data.get('probabilidad'),
            timestamp=data.get('timestamp', datetime.utcnow())
        )
        db.add(db_data)
        db.commit()
        return db_data
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# Nueva función para guardar datos crudos
def save_raw_mqtt_data(data: dict):
    """Guarda datos MQTT crudos en la base de datos"""
    try:
        db = SessionLocal()
        
        # Convertir payload a string si es dict
        payload_str = data['payload']
        if isinstance(payload_str, dict):
            payload_str = json.dumps(payload_str)
            
        raw_data = DBRawMQTTData(
            topic=data['topic'],
            payload=payload_str,
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp']
        )
        
        db.add(raw_data)
        db.commit()
        print(f"✅ Raw MQTT data saved: {data['topic']}")
        
    except Exception as e:
        print(f"❌ Error saving raw MQTT data: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()

# Funciones de consulta
def get_mediciones_por_paciente(paciente_id: int, limit: int = 100):
    db = SessionLocal()
    try:
        return db.query(DBMedicionesData)\
                .filter(DBMedicionesData.paciente_id == paciente_id)\
                .order_by(DBMedicionesData.timestamp.desc())\
                .limit(limit)\
                .all()
    finally:
        db.close()

def get_alertas_por_paciente(paciente_id: int, limit: int = 100):
    db = SessionLocal()
    try:
        return db.query(DBAlertasData)\
                .filter(DBAlertasData.paciente_id == paciente_id)\
                .order_by(DBAlertasData.timestamp.desc())\
                .limit(limit)\
                .all()
    finally:
        db.close()

def get_predicciones_por_paciente(paciente_id: int, limit: int = 100):
    db = SessionLocal()
    try:
        return db.query(DBPrediccionesData)\
                .filter(DBPrediccionesData.paciente_id == paciente_id)\
                .order_by(DBPrediccionesData.timestamp.desc())\
                .limit(limit)\
                .all()
    finally:
        db.close()
