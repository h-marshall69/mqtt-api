from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./esp32_data.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Nueva tabla para mensajes MQTT crudos
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
    temperature = Column(Float)
    humidity = Column(Float)
    light = Column(Float, nullable=True)
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
    db = SessionLocal()
    try:
        # Convertimos el payload a string si es un diccionario
        if isinstance(data.get('payload'), dict):
            data['payload'] = json.dumps(data['payload'])
            
        db_data = DBRawMQTTData(**data)
        db.add(db_data)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving raw MQTT data: {e}")
    finally:
        db.close()

# Funciones de guardado
def save_sensor_data(data: dict):
    db = SessionLocal()
    try:
        db_data = DBSensorData(**data)
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

