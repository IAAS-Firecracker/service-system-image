#!/usr/bin/env python3
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging
import pymysql
from models import *
from dependencies import get_db, StandardResponse


# Charger les variables d'environnement
load_dotenv()

# Configurer le logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration de la base de données
MYSQL_USER = os.getenv('MYSQL_USER', 'firecracker')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'firecracker')
MYSQL_HOST = os.getenv('MYSQL_HOST', 'mysql_db_service_system_image')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
MYSQL_DB = os.getenv('MYSQL_DB', 'service_system_image_db')

DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

# Créer le moteur SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_tables():
    """Crée les tables dans la base de données"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables créées avec succès")
    except Exception as e:
        logger.error(f"Erreur lors de la création des tables: {str(e)}")
        raise

# Fonction pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        from models.model_system_image import SystemImage
        from sqlalchemy.orm import Session
        
        # Utiliser la session locale définie dans ce fichier
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
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
