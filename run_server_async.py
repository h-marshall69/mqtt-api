#!/usr/bin/env python3
"""
Script asíncrono para ejecutar la API FastAPI y el cliente MQTT
"""
import asyncio
import signal
import sys
import os
import uvicorn
import threading
from mqtt.client import start_mqtt_client
from api.main import app
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AsyncMQTTAPIServer:
    def __init__(self, host="0.0.0.0", port=8001):
        self.host = host
        self.port = port
        self.running = False
        self.mqtt_task = None
        self.api_task = None
        
    async def start_mqtt_client_async(self):
        """Inicia el cliente MQTT de forma asíncrona"""
        def mqtt_worker():
            try:
                logger.info("Starting MQTT client...")
                start_mqtt_client()
                logger.info("MQTT client started successfully")
                
                # Mantener el cliente corriendo
                while self.running:
                    import time
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in MQTT client: {e}")
        
        # Ejecutar MQTT client en un hilo separado
        mqtt_thread = threading.Thread(target=mqtt_worker, daemon=True)
        mqtt_thread.start()
        
        # Esperar mientras el hilo esté corriendo
        while self.running and mqtt_thread.is_alive():
            await asyncio.sleep(1)
    
    async def start_api_server_async(self):
        """Inicia el servidor FastAPI de forma asíncrona"""
        try:
            logger.info(f"Starting FastAPI server on {self.host}:{self.port}")
            
            config = uvicorn.Config(
                app=app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Error in API server: {e}")
    
    def signal_handler(self):
        """Maneja las señales de terminación"""
        logger.info("Received termination signal. Shutting down...")
        self.running = False
        
        if self.mqtt_task:
            self.mqtt_task.cancel()
        if self.api_task:
            self.api_task.cancel()
    
    async def start(self):
        """Inicia ambos servicios de forma asíncrona"""
        self.running = True
        
        logger.info("=== Starting Async MQTT API Server ===")
        
        # Crear tareas asíncronas
        self.mqtt_task = asyncio.create_task(self.start_mqtt_client_async())
        self.api_task = asyncio.create_task(self.start_api_server_async())
        
        # Configurar el manejador de señales
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.signal_handler)
        
        try:
            # Ejecutar ambas tareas concurrentemente
            await asyncio.gather(self.mqtt_task, self.api_task)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled. Shutting down gracefully.")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

async def main():
    """Función principal asíncrona"""
    # Configuración del servidor
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", "8001"))
    
    logger.info(f"Configuration:")
    logger.info(f"  - Host: {HOST}")
    logger.info(f"  - Port: {PORT}")
    logger.info(f"  - Working Directory: {os.getcwd()}")
    
    # Verificar archivos necesarios
    if not os.path.exists("api/main.py"):
        logger.error("api/main.py not found. Make sure you're in the mqtt-api directory")
        sys.exit(1)
        
    if not os.path.exists("mqtt/client.py"):
        logger.error("mqtt/client.py not found. Make sure you're in the mqtt-api directory")
        sys.exit(1)
    
    # Iniciar servidor
    server = AsyncMQTTAPIServer(HOST, PORT)
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
