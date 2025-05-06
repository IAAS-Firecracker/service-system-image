import os
import uuid
import shutil
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
import pymysql
from RabbitMQ.publisher.system_image_publisher import system_image_publisher
from config.eureka_client import register_with_eureka, shutdown_eureka
import logging
from config.settings import load_config
import sys



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

# Configuration de la base de données
DATABASE_URL = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DB')}"

# Créer le moteur SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# Définir le chemin de stockage des images
IMAGE_UPLOAD_FOLDER = os.path.join('static', 'img', 'system')

# Fonction pour s'assurer que le dossier de stockage existe
def ensure_upload_folder_exists():
    os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)

# Fonction pour gérer l'upload d'image
def handle_image_upload(file: UploadFile) -> str:
    if file and file.filename:
        # Générer un nom de fichier unique
        filename = file.filename
        # Ajouter un UUID pour éviter les collisions de noms
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        # S'assurer que le dossier existe
        ensure_upload_folder_exists()
        # Chemin complet pour sauvegarder le fichier
        file_path = os.path.join(IMAGE_UPLOAD_FOLDER, unique_filename)
        # Sauvegarder le fichier
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        # Retourner le chemin relatif pour stocker en BD
        return file_path
    return None

# Fonction pour supprimer une image existante
def delete_image_file(image_path: str) -> None:
    if image_path and os.path.exists(image_path):
        os.remove(image_path)

# Définir le modèle de données SQLAlchemy
class SystemImage(Base):
    __tablename__ = 'system_images'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    os_type = Column(String(255), nullable=False)
    version = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    image_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Dépendance pour obtenir la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modèles Pydantic pour la validation des données
class SystemImageBase(BaseModel):
    name: str
    os_type: str
    version: str
    description: Optional[str] = None

class SystemImageCreate(SystemImageBase):
    pass

class SystemImageUpdate(SystemImageBase):
    name: Optional[str] = None
    os_type: Optional[str] = None
    version: Optional[str] = None

class SystemImageResponse(SystemImageBase):
    id: int
    image_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True

# Monter les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

# Définir les routes API
@app.get("/system-images/", response_model=List[SystemImageResponse], tags=["system-images"])
async def list_system_images(db: Session = Depends(get_db)):
    """Liste toutes les images système"""
    system_images = db.query(SystemImage).all()
    return system_images

@app.post("/system-images/", response_model=SystemImageResponse, status_code=status.HTTP_201_CREATED, tags=["system-images"])
async def create_system_image(
    name: str = Form(...),
    os_type: str = Form(...),
    version: str = Form(...),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Crée une nouvelle image système"""
    # Gérer l'upload d'image
    image_path = None
    if image:
        image_path = handle_image_upload(image)
    
    # Créer l'objet SystemImage
    system_image = SystemImage(
        name=name,
        os_type=os_type,
        version=version,
        description=description,
        image_path=image_path
    )
    
    try:
        db.add(system_image)
        db.commit()
        db.refresh(system_image)

        # Publish creation event to RabbitMQ
        system_image_dict = {
            'id': system_image.id,
            'name': system_image.name,
            'os_type': system_image.os_type,
            'version': system_image.version,
            'description': system_image.description,
            'image_path': system_image.image_path
        }
        system_image_publisher.publish_system_image_event('create', system_image_dict)
        
        return system_image
    except Exception as e:
        # En cas d'erreur, supprimer l'image si elle a été uploadée
        if image_path:
            delete_image_file(image_path)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/system-images/{id}", response_model=SystemImageResponse, tags=["system-images"])
async def get_system_image(id: int, db: Session = Depends(get_db)):
    """Obtient une image système par son ID"""
    system_image = db.query(SystemImage).filter(SystemImage.id == id).first()
    if system_image is None:
        raise HTTPException(status_code=404, detail="Image système non trouvée")
    return system_image

@app.put("/system-images/{id}", response_model=SystemImageResponse, tags=["system-images"])
async def update_system_image(
    id: int,
    name: str = Form(...),
    os_type: str = Form(...),
    version: str = Form(...),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Met à jour une image système"""
    system_image = db.query(SystemImage).filter(SystemImage.id == id).first()
    if system_image is None:
        raise HTTPException(status_code=404, detail="Image système non trouvée")
    
    # Gérer l'upload d'image
    old_image_path = system_image.image_path
    new_image_path = old_image_path
    
    if image and image.filename:
        new_image_path = handle_image_upload(image)
        # Supprimer l'ancienne image si elle existe
        if old_image_path:
            delete_image_file(old_image_path)
    
    # Mettre à jour les attributs
    system_image.name = name
    system_image.os_type = os_type
    system_image.version = version
    system_image.description = description
    system_image.image_path = new_image_path
    system_image.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(system_image)
        
        # Publish update event to RabbitMQ
        system_image_dict = {
            'id': system_image.id,
            'name': system_image.name,
            'os_type': system_image.os_type,
            'version': system_image.version,
            'description': system_image.description,
            'image_path': system_image.image_path
        }
        system_image_publisher.publish_system_image_event('update', system_image_dict)
        
        return system_image
    except Exception as e:
        # En cas d'erreur, si une nouvelle image a été uploadée, la supprimer
        if new_image_path != old_image_path:
            delete_image_file(new_image_path)
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/system-images/{id}", status_code=status.HTTP_200_OK, tags=["system-images"])
async def delete_system_image(id: int, db: Session = Depends(get_db)):
    """Supprime une image système"""
    system_image = db.query(SystemImage).filter(SystemImage.id == id).first()
    if system_image is None:
        raise HTTPException(status_code=404, detail="Image système non trouvée")
    
    # Sauvegarder le chemin de l'image pour la supprimer après
    image_path = system_image.image_path
    
    try:
        # Capture system image data before deletion for the event
        system_image_dict = {
            'id': system_image.id,
            'name': system_image.name,
            'os_type': system_image.os_type,
            'version': system_image.version,
            'description': system_image.description,
            'image_path': system_image.image_path
        }
        
        # Delete from database
        db.delete(system_image)
        db.commit()
        
        # Publish deletion event to RabbitMQ
        system_image_publisher.publish_system_image_event('delete', system_image_dict)
        
        # Supprimer le fichier image s'il existe
        if image_path:
            delete_image_file(image_path)
            
        return {"message": "Image système supprimée avec succès"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/system-images/search/{name}", response_model=List[SystemImageResponse], tags=["system-images"])
async def search_system_images(name: str, db: Session = Depends(get_db)):
    """Recherche des images système par nom"""
    system_images = db.query(SystemImage).filter(SystemImage.name.like(f"%{name}%")).all()
    return system_images

@app.get("/system-images/os-type/{os_type}", response_model=List[SystemImageResponse], tags=["system-images"])
async def get_system_images_by_os_type(os_type: str, db: Session = Depends(get_db)):
    """Obtient les images système par type de système d'exploitation"""
    system_images = db.query(SystemImage).filter(SystemImage.os_type == os_type).all()
    return system_images

@app.get("/health", tags=["health"])
async def health_check():
    """Vérifie la santé de l'application"""
    return {"status": "UP", "service": "SERVICE-SYSTEM-IMAGE"}

# Fonction pour créer les tables dans la base de données
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tables créées avec succès.")

# Fonction pour initialiser la base de données
def init_database():
    try:
        logger.info("Initialisation de la base de données...")
        # Récupérer les informations de connexion depuis les variables d'environnement
        mysql_host = os.getenv('MYSQL_HOST')
        mysql_port = int(os.getenv('MYSQL_PORT'))
        mysql_user = os.getenv('MYSQL_USER')
        mysql_password = os.getenv('MYSQL_PASSWORD')
        mysql_db = os.getenv('MYSQL_DB')
        
        logger.info(f"Connexion à MySQL: {mysql_host}:{mysql_port} avec l'utilisateur {mysql_user}")
        
        # Créer la base de données si elle n'existe pas
        conn = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password
        )
        
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {mysql_db}")
        conn.commit()
        
        logger.info(f"Base de données '{mysql_db}' créée ou déjà existante.")
        
        cursor.close()
        conn.close()
        
        # Maintenant importer l'application pour créer les tables
        from app import create_tables
        
        # Utiliser la fonction create_tables définie dans app.py
        create_tables()
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
        return False

# Fonction pour ajouter des données de test
def seed_database():
    try:
        logger.info("Ajout des données de test...")
        from app import SessionLocal, SystemImage
        from sqlalchemy.orm import Session
        
        # Données de test
        test_images = [
            {
                'name': 'Ubuntu 22.04 LTS',
                'os_type': 'ubuntu-22.04',
                'version': '22.04',
                'description': 'Ubuntu 22.04 LTS (Jammy Jellyfish) est une version LTS (Long Term Support) d\'Ubuntu, offrant 5 ans de support et de mises à jour de sécurité.',
                'image_path': 'static/img/system/ubuntu-22.04.png'
            },
            {
                'name': 'Ubuntu 24.04 LTS',
                'os_type': 'ubuntu-24.04',
                'version': '24.04',
                'description': 'Ubuntu 24.04 LTS est la dernière version LTS d\'Ubuntu, offrant les dernières fonctionnalités et améliorations.',
                'image_path': 'static/img/system/ubuntu-24.04.png'
            }
        ]
        
        # Créer une session de base de données
        db = SessionLocal()
        try:
            # Vérifier si des données existent déjà
            existing_count = db.query(SystemImage).count()
            if existing_count > 0:
                logger.info(f"{existing_count} images système existent déjà dans la base de données.")
                return True
            
            # Ajouter les images système de test
            for image_data in test_images:
                image = SystemImage(**image_data)
                db.add(image)
            
            # Sauvegarder les changements
            db.commit()
            logger.info(f"{len(test_images)} images système ajoutées avec succès.")
            return True
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout des données de test: {e}")
        return False

# Point d'entrée principal
if __name__ == '__main__':
    # Récupérer le port de l'application depuis les variables d'environnement
    app_port = int(os.getenv('APP_PORT', 5001))
    logger.info(f"Port de l'application configuré: {app_port}")
    
    # Initialiser la base de données
    if init_database():
        create_tables()
        # Ajouter des données de test
        seed_database()
    
        # Démarrer l'application FastAPI avec uvicorn
        import uvicorn
        logger.info(f"Démarrage de l'application FastAPI sur le port {app_port}...")
        uvicorn.run("app:app", host="0.0.0.0", port=app_port, reload=True)
    else:
        logger.error("Impossible de démarrer l'application en raison d'erreurs d'initialisation.")
        sys.exit(1)