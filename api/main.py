from fastapi import FastAPI
from mqtt.client import start_mqtt_client
from database import SessionLocal
from api.routers import data

app = FastAPI()

# Incluir routers
app.include_router(data.router)

@app.on_event("startup")
async def startup_event():
    start_mqtt_client()

@app.get("/")
async def root():
    return {"message": "ESP32 MQTT API Server"}
