import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from RabbitMQ.publisher.system_image_publisher import system_image_publisher
from config.eureka_client import register_with_eureka, shutdown_eureka
import logging
from config.settings import load_config
import sys
from database import init_database, create_tables, seed_database
from routes.route_system_image import router as system_image_router
from fastapi.staticfiles import StaticFiles


# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Importer et exécuter les configurations depuis settings.py si disponible
logger.info("Chargement des configurations...")
try:
    load_config()
    logger.info("Configurations chargées avec succès")
except ImportError:
    logger.warning("Module config.settings non trouvé, utilisation des variables d'environnement par défaut")
except Exception as e:
    logger.error(f"Erreur lors du chargement des configurations: {e}")


# Initialiser l'application FastAPI
app = FastAPI(
    title="System Image API",
    description="API pour gérer les images système",
    version="1.0.0",
    docs_url="/swagger"
)

# Ajouter le middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to RabbitMQ on startup
@app.on_event("startup")
async def startup_event():
    #connect Eureka
    await register_with_eureka()
    # Initialiser la base de données
    if init_database():
        create_tables()
        # Ajouter des données de test
        seed_database()
    # Connect to RabbitMQ and set up the exchange
    system_image_publisher.connect()
    print(f"Connected to RabbitMQ exchange: {system_image_publisher.exchange_name}")

# Close RabbitMQ connection on shutdown
@app.on_event("shutdown")
async def shutdown_event():
    #deregister Eureka
    await shutdown_eureka()
    system_image_publisher.close()
    print("Closed RabbitMQ connection")


# Monter les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health", tags=["health"])
async def health_check():
    """Vérifie la santé de l'application"""
    return {"status": "UP", "service": "SERVICE-SYSTEM-IMAGE"}

# Inclure les routers
app.include_router(system_image_router)


# Point d'entrée principal
if __name__ == '__main__':
    # Récupérer le port de l'application depuis les variables d'environnement
    app_port = int(os.getenv('APP_PORT', 5001))
    logger.info(f"Port de l'application configuré: {app_port}")
    
    # # Initialiser la base de données
    # if init_database():
    #     create_tables()
    #     # Ajouter des données de test
    #     seed_database()
    
        # Démarrer l'application FastAPI avec uvicorn
    import uvicorn
    logger.info(f"Démarrage de l'application FastAPI sur le port {app_port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=app_port, reload=True)
    # else:
    #     logger.error("Impossible de démarrer l'application en raison d'erreurs d'initialisation.")
    #     sys.exit(1)