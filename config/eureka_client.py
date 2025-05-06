import os
from py_eureka_client import eureka_client
from dotenv import load_dotenv

load_dotenv()

async def register_with_eureka():
    try:
        eureka_url = os.getenv('EUREKA_SERVER', 'http://localhost:8761/eureka/')
        app_name = os.getenv('APP_NAME', 'service-system-image')
        app_port = int(os.getenv('APP_PORT', '5001'))
        
        
        import socket
        try:
            # This gets the local IP address that would be used to connect to an external server
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = os.getenv('APP_HOST', '0.0.0.0')
        
        app_host = local_ip
        
        if not eureka_url or not app_name:
            print(f"Configuration Eureka incomplète: eureka_url={eureka_url}, app_name={app_name}")
            return
            
        print(f"Enregistrement auprès d'Eureka: {app_name} vers {eureka_url}")
        
        await eureka_client.init_async(
            eureka_server=eureka_url,
            app_name=app_name,
            instance_port=app_port,
            instance_host=app_host,
            renewal_interval_in_secs=30,
            duration_in_secs=90,
            metadata={
                "zone": "primary",
                "securePortEnabled": "false",
                "securePort": "443",
                "statusPageUrl": f"http://{app_host}:{app_port}/api/service-system-image/info",
                "healthCheckUrl": f"http://{app_host}:{app_port}/api/service-system-image/health"
            }
        )
        print(f"Enregistrement auprès d'Eureka réussi")
    except Exception as e:
        print(f"Erreur lors de l'enregistrement auprès d'Eureka: {e}")

async def shutdown_eureka():
    try:
        await eureka_client.stop_async()
        print("Désenregistrement d'Eureka réussi")
    except Exception as e:
        print(f"Erreur lors du désenregistrement d'Eureka: {e}")
