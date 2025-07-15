import paho.mqtt.client as mqtt
import random
import time
import json
from datetime import datetime

# Configuración MQTT (debe coincidir con tu servidor)
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPICS = {
    "sensors": "esp32/sensors",
    "alarms": "esp32/alarms",
    "button": "esp32/button",
    "rgb": "esp32/rgb"
}

class ESP32Simulator:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        
    def on_connect(self, client, userdata, flags, rc):
        print(f"Conectado al broker con código: {rc}")
        
    def connect(self):
        self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.client.loop_start()
        
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        
    def generate_sensor_data(self):
        """Genera datos de sensores simulados"""
        return {
            "temperature": round(random.uniform(20.0, 30.0), 2),
            "humidity": round(random.uniform(40.0, 80.0), 2),
            "light": round(random.uniform(0, 100.0), 2),
            "timestamp": datetime.now().isoformat()
        }
        
    def generate_alarm_data(self):
        """Genera datos de alarma simulados"""
        return {
            "type": random.choice(["movimiento", "temperatura", "humedad", "luz"]),
            "state": random.choice([True, False]),
            "timestamp": datetime.now().isoformat()
        }
        
    def generate_button_data(self):
        """Genera datos de botón simulados"""
        return {
            "state": random.choice([True, False]),
            "timestamp": datetime.now().isoformat()
        }
        
    def generate_rgb_data(self):
        """Genera datos RGB simulados"""
        return {
            "red": random.randint(0, 255),
            "green": random.randint(0, 255),
            "blue": random.randint(0, 255),
            "timestamp": datetime.now().isoformat()
        }
        
    def run_simulation(self, interval=5):
        """Ejecuta la simulación con el intervalo especificado (en segundos)"""
        try:
            print("Iniciando simulación ESP32...")
            while True:
                # Publicar datos de sensores
                sensor_data = self.generate_sensor_data()
                self.client.publish(TOPICS["sensors"], json.dumps(sensor_data))
                print(f"Publicado en {TOPICS['sensors']}: {sensor_data}")
                
                # Publicar datos de alarma (50% de probabilidad)
                if random.random() > 0.5:
                    alarm_data = self.generate_alarm_data()
                    self.client.publish(TOPICS["alarms"], json.dumps(alarm_data))
                    print(f"Publicado en {TOPICS['alarms']}: {alarm_data}")
                
                # Publicar estado de botón (30% de probabilidad)
                if random.random() > 0.7:
                    button_data = self.generate_button_data()
                    self.client.publish(TOPICS["button"], json.dumps(button_data))
                    print(f"Publicado en {TOPICS['button']}: {button_data}")
                
                # Publicar valores RGB (20% de probabilidad)
                if random.random() > 0.8:
                    rgb_data = self.generate_rgb_data()
                    self.client.publish(TOPICS["rgb"], json.dumps(rgb_data))
                    print(f"Publicado en {TOPICS['rgb']}: {rgb_data}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nDeteniendo simulación...")
            self.disconnect()

if __name__ == "__main__":
    simulator = ESP32Simulator()
    simulator.connect()
    simulator.run_simulation(interval=5)  # Intervalo de 5 segundos
