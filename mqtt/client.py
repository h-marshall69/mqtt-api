import paho.mqtt.client as mqtt
from database import (
    save_sensor_data,
    save_alarm_data,
    save_button_data,
    save_rgb_data
)
import json
from datetime import datetime
from typing import Dict, Any

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPICS = [
    "esp32/sensors",
    "esp32/alarms",
    "esp32/button",
    "esp32/rgb"
]

def parse_timestamp(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Asegura que el timestamp esté en el formato correcto"""
    if 'timestamp' in payload:
        try:
            # Si el timestamp viene como string, lo convertimos a datetime
            if isinstance(payload['timestamp'], str):
                payload['timestamp'] = datetime.fromisoformat(payload['timestamp'])
        except (ValueError, TypeError):
            payload['timestamp'] = datetime.utcnow()
    else:
        payload['timestamp'] = datetime.utcnow()
    return payload

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    for topic in TOPICS:
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received message on {msg.topic}: {payload}")
        
        # Procesamiento común del timestamp
        payload = parse_timestamp(payload)
        
        # Guardar en la base de datos según el topic
        if msg.topic == "esp32/sensors":
            save_sensor_data(payload)
        elif msg.topic == "esp32/alarms":
            save_alarm_data(payload)
        elif msg.topic == "esp32/button":
            save_button_data(payload)
        elif msg.topic == "esp32/rgb":
            save_rgb_data(payload)
            
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

def start_mqtt_client():
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("MQTT client started successfully")
    except Exception as e:
        print(f"Failed to start MQTT client: {e}")

def publish(topic: str, message: Dict[str, Any]):
    try:
        message = parse_timestamp(message)
        client.publish(topic, json.dumps(message))
        print(f"Published to {topic}: {message}")
    except Exception as e:
        print(f"Error publishing message: {e}")
