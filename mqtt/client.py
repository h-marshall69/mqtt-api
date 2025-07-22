import paho.mqtt.client as mqtt
import requests
from database import (
    save_mediciones_data,
    save_raw_mqtt_data
)
import json
import os
from datetime import datetime
from typing import Dict, Any

# Configuración
API_ENDPOINT = os.getenv("API_ENDPOINT", "http://3.142.136.76:8000/api/v1/pacientes/identificador/")

# Configuración MQTT - Usar variables de entorno para credenciales
MQTT_BROKER = os.getenv("MQTT_BROKER", "3.142.136.76")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "abadeer")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", f"python_client_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

TOPICS = [
    "esp32/mediciones",
    "esp32/#"  # Wildcard para capturar todo
]

def get_paciente_id():
    """Consulta el endpoint para obtener el ID de paciente"""
    try:
        response = requests.get(API_ENDPOINT)
        if response.status_code == 200:
            return response.json().get('identificador')
        return None
    except Exception as e:
        print(f"Error consultando endpoint: {str(e)}")
        return None

def parse_timestamp(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Asegura que el timestamp esté en el formato correcto"""
    if 'timestamp' in payload:
        try:
            if isinstance(payload['timestamp'], str):
                payload['timestamp'] = datetime.fromisoformat(payload['timestamp'])
        except (ValueError, TypeError):
            payload['timestamp'] = datetime.utcnow()
    else:
        payload['timestamp'] = datetime.utcnow()
    return payload

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker"""
    if rc == 0:
        print(f"✅ Connected successfully to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
        for topic in TOPICS:
            result = client.subscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ Subscribed to {topic}")
            else:
                print(f"❌ Failed to subscribe to {topic}")
    else:
        error_messages = {
            1: "Connection refused - incorrect protocol version",
            2: "Connection refused - invalid client identifier", 
            3: "Connection refused - server unavailable",
            4: "Connection refused - bad username or password",
            5: "Connection refused - not authorised"
        }
        print(f"❌ Connection failed with code {rc}: {error_messages.get(rc, 'Unknown error')}")

def on_disconnect(client, userdata, rc):
    """Callback cuando se desconecta del broker"""
    if rc != 0:
        print(f"⚠️  Unexpected disconnection from MQTT broker (code: {rc})")
    else:
        print("🔌 Disconnected from MQTT broker")

def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje"""
    try:
        # Decodificar mensaje
        raw_payload = msg.payload.decode('utf-8')
        print(f"📨 Received on {msg.topic}: {raw_payload}")
        
        # Intentar parsear como JSON
        try:
            payload = json.loads(raw_payload)
            payload_type = "json"
            print(f"✅ Parsed as JSON: {payload}")
        except json.JSONDecodeError:
            payload = raw_payload
            payload_type = "text"
            print(f"ℹ️  Treating as text: {payload}")
        
        identificador = get_paciente_id()
        # Guardar SIEMPRE el mensaje crudo
        raw_data = {
            "topic": msg.topic,
            "paciente_id": identificador,
            "payload": json.dumps(payload) if payload_type == "json" else payload,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            save_raw_mqtt_data(raw_data)
            print(f"💾 Saved raw data to database")
        except Exception as db_error:
            print(f"❌ Error saving raw data: {db_error}")


        # Procesar datos específicos si son JSON válido
        if payload_type == "json":
            try:
                if msg.topic == "esp32/mediciones":
                    if not identificador:
                        print("⚠️ No se pudo obtener paciente_id")
                        return

                    datos_completos = {
                        **payload,
                        "paciente_identificador": identificador,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    save_mediciones_data(datos_completos)
                    print(f"💾 Saved mediciones data Abadeer")
            except Exception as parse_error:
                print(f"⚠️  Error saving parsed data: {parse_error}")
            
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        # Guardar incluso los mensajes con errores
        try:
            save_raw_mqtt_data({
                "topic": msg.topic,
                "payload": str(msg.payload.decode('utf-8', errors='ignore')),
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            })
        except Exception as save_error:
            print(f"❌ Error saving error message: {save_error}")

def on_subscribe(client, userdata, mid, granted_qos):
    """Callback cuando se confirma la suscripción"""
    print(f"✅ Subscription confirmed with QoS: {granted_qos}")

def on_log(client, userdata, level, buf):
    """Callback para logs del cliente MQTT"""
    print(f"🔍 MQTT Log: {buf}")

# Crear cliente con ID único
client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=True)

# Configurar callbacks
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_subscribe = on_subscribe
client.on_log = on_log  # Solo para debugging

# Configurar autenticación
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
print(f"🔐 Using credentials: {MQTT_USERNAME}/{'*' * len(MQTT_PASSWORD)}")

def start_mqtt_client():
    """Inicia el cliente MQTT con reintentos"""
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print(f"🔄 Attempting to connect to MQTT broker... (attempt {retry_count + 1})")
            print(f"📡 Broker: {MQTT_BROKER}:{MQTT_PORT}")
            
            # Conectar al broker
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            
            # Iniciar el loop
            client.loop_start()
            print("✅ MQTT client started successfully")
            return True
            
        except Exception as e:
            retry_count += 1
            print(f"❌ Failed to start MQTT client (attempt {retry_count}): {e}")
            
            if retry_count < max_retries:
                import time
                wait_time = 5 * retry_count
                print(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"❌ Max retries ({max_retries}) reached. Could not connect to MQTT broker.")
                return False

def stop_mqtt_client():
    """Detiene el cliente MQTT"""
    try:
        client.loop_stop()
        client.disconnect()
        print("🔌 MQTT client stopped")
    except Exception as e:
        print(f"❌ Error stopping MQTT client: {e}")

def publish(topic: str, message: Dict[str, Any]):
    """Publica un mensaje al broker"""
    try:
        message = parse_timestamp(message)
        result = client.publish(topic, json.dumps(message))
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"📤 Published to {topic}: {message}")
        else:
            print(f"❌ Failed to publish to {topic}: {result.rc}")
    except Exception as e:
        print(f"❌ Error publishing message: {e}")

# Para testing directo
if __name__ == "__main__":
    print("🚀 Starting MQTT client for testing...")
    start_mqtt_client()
    
    try:
        import time
        print("⏳ Waiting for messages... (Press Ctrl+C to stop)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping MQTT client...")
        stop_mqtt_client()
