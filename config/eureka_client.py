import sys
import py_eureka_client.eureka_client as eureka_client
import os
import dotenv
import logging
import signal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
dotenv.load_dotenv()

def init_eureka():
    # Get the container name from the environment variable or use a fallback method
    container_name = os.environ.get('HOSTNAME', 'default-instance')
    # Use the container name or a unique identifier for the instance ID
    instance_id = f"{os.getenv('APP_NAME')}-{container_name}"
    
    # Get local IP address for better service discovery
    import socket
    try:
        # This gets the local IP address that would be used to connect to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"  # Fallback to localhost if unable to determine IP
    
    print(f"Registering with Eureka using IP: {local_ip} and port: {os.getenv('APP_PORT')}")
    
    eureka_client.init(
        eureka_server=os.getenv('EUREKA_SERVER'),
        app_name=os.getenv('APP_NAME'),
        instance_ip=local_ip,  # Use actual IP instead of container name
        instance_port=os.getenv('APP_PORT'),
        instance_host=local_ip,  # Use actual IP for host too
        instance_id=instance_id,
        renewal_interval_in_secs=30,  # Heartbeat interval
        duration_in_secs=90,
        # Add context path for Swagger UI
        home_page_url=f"http://{local_ip}:{os.getenv('APP_PORT')}/swagger",
        status_page_url=f"http://{local_ip}:{os.getenv('APP_PORT')}/swagger",
        health_check_url=f"http://{local_ip}:{os.getenv('APP_PORT')}/api/health"
    )
    


def deregister_and_exit(signal, frame):
    eureka_client.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, deregister_and_exit)
signal.signal(signal.SIGTERM, deregister_and_exit)
