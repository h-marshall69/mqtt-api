from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./esp32_data.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Tabla: Mensajes MQTT crudos
class DBRawMQTTData(Base):
    __tablename__ = "raw_mqtt_data"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String)
    payload = Column(String)  # Almacenamos como string JSON
    timestamp = Column(DateTime, default=datetime.utcnow)

# Tabla: Datos del Sensor
class DBSensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    sensor = Column(String, nullable=True)  # Nuevo
    temperature = Column(Float)
    humidity = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Tabla: Datos de la Alarma
class DBAlarmData(Base):
    __tablename__ = "alarm_data"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    state = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Tabla: Datos del Botón
class DBButtonData(Base):
    __tablename__ = "button_data"
    
    id = Column(Integer, primary_key=True, index=True)
    state = Column(Boolean)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Tabla: Datos RGB
class DBRGBData(Base):
    __tablename__ = "rgb_data"
    
    id = Column(Integer, primary_key=True, index=True)
    red = Column(Integer)
    green = Column(Integer)
    blue = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

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

# Funciones de guardado
def save_sensor_data(data: dict):
    db = SessionLocal()
    try:
        db_data = DBSensorData(
            sensor=data.get('sensor'),
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            timestamp = datetime.fromtimestamp(data['timestamp']) if 'timestamp' in data else datetime.utcnow()
        )
        db.add(db_data)
        db.commit()
    finally:
        db.close()

def save_alarm_data(data: dict):
    db = SessionLocal()
    try:
        db_data = DBAlarmData(**data)
        db.add(db_data)
        db.commit()
    finally:
        db.close()

def save_button_data(data: dict):
    db = SessionLocal()
    try:
        db_data = DBButtonData(**data)
        db.add(db_data)
        db.commit()
    finally:
        db.close()

def save_rgb_data(data: dict):
    db = SessionLocal()
    try:
        db_data = DBRGBData(**data)
        db.add(db_data)
        db.commit()
    finally:
        db.close()

