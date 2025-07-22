#!/usr/bin/env python3
"""
Script para debuggear la conexión MQTT
"""
import sys
import os
sys.path.append(os.getcwd())

from mqtt.client import start_mqtt_client, client, MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, TOPICS
from database import SessionLocal, DBRawMQTTData, DBSensorData
import time
import json

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    try:
        print("🔍 Testing database connection...")
        db = SessionLocal()
        
        # Probar consulta simple
        count = db.query(DBRawMQTTData).count()
        print(f"✅ Database connected. Raw MQTT records: {count}")
        
        sensor_count = db.query(DBSensorData).count()
        print(f"✅ Sensor data records: {sensor_count}")
        
        db.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_mqtt_connection():
    """Prueba la conexión MQTT"""
    try:
        print("🔍 Testing MQTT connection...")
        print(f"📡 Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"🔐 Username: {MQTT_USERNAME}")
        print(f"📋 Topics: {TOPICS}")
        
        success = start_mqtt_client()
        if success:
            print("✅ MQTT client started")
            return True
        else:
            print("❌ MQTT client failed to start")
            return False
    except Exception as e:
        print(f"❌ MQTT connection error: {e}")
        return False

def simulate_message():
    """Simula un mensaje para probar el procesamiento"""
    try:
        print("🔍 Testing message processing...")
        from mqtt.client import on_message
        from unittest.mock import MagicMock
        
        # Crear mensaje simulado
        mock_msg = MagicMock()
        mock_msg.topic = "esp32/sensors"
        mock_msg.payload.decode.return_value = '{"device":"ESP32","sensor":"DHT11","temperature":18,"humidity":60.7,"timestamp":370099}'
        
        # Procesar mensaje
        on_message(None, None, mock_msg)
        print("✅ Message processing test completed")
        
    except Exception as e:
        print(f"❌ Message processing error: {e}")

def check_recent_data():
    """Revisa los datos más recientes en la base de datos"""
    try:
        print("🔍 Checking recent data...")
        db = SessionLocal()
        
        # Últimos 5 mensajes crudos
        raw_data = db.query(DBRawMQTTData).order_by(DBRawMQTTData.timestamp.desc()).limit(5).all()
        print(f"📊 Last {len(raw_data)} raw messages:")
        for i, data in enumerate(raw_data, 1):
            print(f"  {i}. {data.timestamp} | {data.topic} | {data.payload[:50]}...")
        
        # Últimos datos de sensores
        sensor_data = db.query(DBSensorData).order_by(DBSensorData.timestamp.desc()).limit(3).all()
        print(f"📊 Last {len(sensor_data)} sensor readings:")
        for i, data in enumerate(sensor_data, 1):
            print(f"  {i}. {data.timestamp} | T:{data.temperature}°C | H:{data.humidity}%")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Error checking recent data: {e}")

def main():
    print("🔧 MQTT API Debug Tool")
    print("=" * 50)
    
    # Test 1: Database
    if not test_database_connection():
        print("❌ Database test failed. Check your database.py configuration.")
        return
    
    # Test 2: Message processing simulation
    simulate_message()
    
    # Test 3: MQTT Connection
    if not test_mqtt_connection():
        print("❌ MQTT test failed. Check your broker configuration and credentials.")
        return
    
    print("\n⏳ Waiting for live messages for 30 seconds...")
    print("   (You should see messages if your ESP32 is sending data)")
    
    try:
        for i in range(30):
            time.sleep(1)
            if (i + 1) % 10 == 0:
                print(f"⏰ {30 - (i + 1)} seconds remaining...")
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    
    # Test 4: Check what we received
    check_recent_data()
    
    print("\n✅ Debug completed!")

if __name__ == "__main__":
    main()
