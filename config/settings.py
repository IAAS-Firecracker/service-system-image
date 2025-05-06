
import os
from pathlib import Path
import logging
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
import requests 

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()

def get_config(application_name, url):
    if not application_name or not url:
        logger.warning(f"Paramètres manquants: application_name={application_name}, url={url}")
        return None
        
    try:
        logger.info(f"Tentative de récupération de la configuration pour {application_name} depuis {url}")
        response = requests.get(f"{url}/{application_name}/profile", timeout=5)

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Erreur lors de la récupération de la configuration: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Exception lors de la requête vers le serveur de configuration: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue dans get_config: {e}")
        return None

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
        # Vérifier les variables d'environnement requises
        app_name = os.getenv('APP_NAME')
        config_uri = os.getenv('SERVICE_CONFIG_URI')
        
        if not app_name or not config_uri:
            logger.warning(f"Variables d'environnement manquantes: APP_NAME={app_name}, SERVICE_CONFIG_URI={config_uri}")
            logger.info("Utilisation des configurations par défaut")
            return
            
        # Récupérer la configuration depuis le serveur de configuration
        CONF = get_config(app_name, config_uri)
        
        if not CONF:
            logger.warning("Impossible de récupérer la configuration, utilisation des configurations par défaut")
            return
            
        # Extraire les propriétés de la source
        if 'propertySources' not in CONF or not CONF.get("propertySources"):
            logger.warning("Format de configuration invalide, utilisation des configurations par défaut")
            return
            
        properties = CONF.get("propertySources")[0].get('source')
        

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
            'APP_PORT': int(properties.get('server.port')),
            'MYSQL_HOST': MYSQL['host'],
            'MYSQL_PORT': MYSQL['port'],
            'MYSQL_DB': MYSQL['database'],
            'MYSQL_USER': MYSQL['username'],
            'MYSQL_PASSWORD': MYSQL['password'],
            'RABBITMQ_HOST': RABBITMQ['host'],
            'RABBITMQ_PORT': RABBITMQ['port'],
            'RABBITMQ_USER': RABBITMQ['username'],
            'RABBITMQ_PASSWORD': RABBITMQ['password'],
            'EUREKA_SERVER': properties.get('eureka.client.service-url.defaultZone'),
        }
        
        # Mettre à jour les variables d'environnement en mémoire
        update_env_vars(env_updates)
        
        # Mettre à jour le fichier .env
        update_env_file(env_updates)
        
        logger.info(f"Chargement de la configuration réussi")
    
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la configuration: {e}")
        return None, None, None, None
