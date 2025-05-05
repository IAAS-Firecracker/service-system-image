
import os
from pathlib import Path
from .config_client import get_config 
from .eureka_client import *
import logging
import os
import dotenv
import sys
from pathlib import Path
from .config_client import get_config
from .eureka_client import init_eureka

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
dotenv.load_dotenv()

# Fonction pour mettre à jour les variables d'environnement
def update_env_file(env_vars):
    try:
        env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
        
        # Lire le fichier .env existant
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Créer un dictionnaire des variables existantes
        env_dict = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
        
        # Mettre à jour avec les nouvelles valeurs
        env_dict.update(env_vars)
        
        # Écrire le fichier .env mis à jour
        with open(env_path, 'w') as f:
            for key, value in env_dict.items():
                f.write(f"{key}={value}\n")
        
        logger.info(f"Fichier .env mis à jour avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du fichier .env: {e}")
        return False

# Fonction pour mettre à jour les variables d'environnement en mémoire
def update_env_vars(env_vars):
    for key, value in env_vars.items():
        os.environ[key] = str(value)
    logger.info("Variables d'environnement mises à jour en mémoire")


def load_config():
    try:
        # Récupérer la configuration depuis le serveur de configuration
        CONF = get_config(os.getenv('APP_NAME'), os.getenv('SERVICE_CONFIG_URI'))
        logger.info("Configuration récupérée avec succès CLOUD-CONF")
        
        # Extraire les propriétés de la source
        properties = CONF.get("propertySources")[0].get('source')
        
        # Configuration Eureka
        eureka_conf = {
            'server': properties.get('eureka.client.service-url.defaultZone'),
            'app_name': os.getenv('APP_NAME').upper(),
            'port': int(properties.get('server.port'))
        }
        logger.info(f"Configuration Eureka: {eureka_conf}")
        
        # Configuration RabbitMQ
        logger.info(f"Configuration RabbitMQ: {properties.get('spring.rabbitmq.host')}")
        RABBITMQ = {
            'host': properties.get('spring.rabbitmq.host'),
            'port': properties.get('spring.rabbitmq.port', '5672'),
            'username': properties.get('spring.rabbitmq.username', 'guest'),
            'password': properties.get('spring.rabbitmq.password', 'guest')
        }
        logger.info(f"Configuration RabbitMQ: {RABBITMQ}")
        
        # Configuration MySQL
        db_url = properties.get('spring.datasource.url', '')
        if '://' in db_url:
            db_parts = db_url.split('//')[-1].split('/')
            host_port = db_parts[0].split(':') if ':' in db_parts[0] else [db_parts[0], '3306']
            database = db_parts[-1] if len(db_parts) > 1 else os.getenv('MYSQL_DB', 'service_system_image_db')
        else:
            host_port = [os.getenv('MYSQL_HOST', 'localhost'), os.getenv('MYSQL_PORT', '3306')]
            database = os.getenv('MYSQL_DB', 'service_system_image_db')
            
        MYSQL = {
            'host': host_port[0],
            'port': host_port[1],
            'database': database,
            'username': properties.get('spring.datasource.username', os.getenv('MYSQL_USER', 'root')),
            'password': properties.get('spring.datasource.password', os.getenv('MYSQL_PASSWORD', 'root'))
        }
        logger.info(f"Configuration MySQL: {MYSQL}")
        
        # Mettre à jour les variables d'environnement
        env_updates = {
            'APP_PORT': str(eureka_conf['port']),
            'MYSQL_HOST': MYSQL['host'],
            'MYSQL_PORT': MYSQL['port'],
            'MYSQL_DB': MYSQL['database'],
            'MYSQL_USER': MYSQL['username'],
            'MYSQL_PASSWORD': MYSQL['password'],
            'RABBITMQ_HOST': RABBITMQ['host'],
            'RABBITMQ_PORT': RABBITMQ['port'],
            'RABBITMQ_USER': RABBITMQ['username'],
            'RABBITMQ_PASSWORD': RABBITMQ['password'],
            'EUREKA_SERVER': eureka_conf['server']
        }
        
        # Mettre à jour les variables d'environnement en mémoire
        update_env_vars(env_updates)
        
        # Mettre à jour le fichier .env
        update_env_file(env_updates)
        
        # Initialiser le client Eureka
        init_eureka()
        
        return CONF, eureka_conf, RABBITMQ, MYSQL
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration: {e}")
        return None, None, None, None

# Charger la configuration
CONF, eureka_conf, RABBITMQ, MYSQL = load_config()

# Si la configuration n'a pas pu être chargée, utiliser les valeurs par défaut
if CONF is None:
    logger.info("Utilisation des valeurs par défaut...")
    
    # Valeurs par défaut si le serveur de configuration n'est pas disponible
    eureka_conf = {
        'server': 'http://localhost:8761/eureka/',
        'app_name': os.getenv('APP_NAME', 'service-system-image').upper(),
        'port': int(os.getenv('APP_PORT', 5001))
    }
    
    RABBITMQ = {
        'host': 'localhost',
        'port': '5672',
        'username': 'guest',
        'password': 'guest'
    }
    
    MYSQL = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': os.getenv('MYSQL_PORT', '3306'),
        'database': os.getenv('MYSQL_DB', 'service_system_image_db'),
        'username': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', 'root')
    }
    
    # Mettre à jour les variables d'environnement avec les valeurs par défaut
    env_updates = {
        'APP_PORT': str(eureka_conf['port']),
        'MYSQL_HOST': MYSQL['host'],
        'MYSQL_PORT': MYSQL['port'],
        'MYSQL_DB': MYSQL['database'],
        'MYSQL_USER': MYSQL['username'],
        'MYSQL_PASSWORD': MYSQL['password'],
        'RABBITMQ_HOST': RABBITMQ['host'],
        'RABBITMQ_PORT': RABBITMQ['port'],
        'RABBITMQ_USER': RABBITMQ['username'],
        'RABBITMQ_PASSWORD': RABBITMQ['password'],
        'EUREKA_SERVER': eureka_conf['server']
    }
    
    # Mettre à jour les variables d'environnement en mémoire
    update_env_vars(env_updates)
    
    # Mettre à jour le fichier .env
    update_env_file(env_updates)





