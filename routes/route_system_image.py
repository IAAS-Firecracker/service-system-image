#!/usr/bin/env python3
import os
import uuid
import shutil
from fastapi import Depends, HTTPException, UploadFile, File, Form, status,Path
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.model_system_image import SystemImage, SystemImageResponse
from dotenv import load_dotenv
from RabbitMQ.publisher.system_image_publisher import system_image_publisher
from datetime import datetime
from dependencies import get_db


router = APIRouter(
    prefix="/api/service-system-image",
    tags=["system-image"],
    responses={404: {"description": "Not found"}},
)

# Charger les variables d'environnement avant d'importer les autres modules
load_dotenv()


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


# Monter les fichiers statiques
router.mount("/static", StaticFiles(directory="static"), name="static")

# Définir les routes API
@router.get("/system-images/", response_model=List[SystemImageResponse])
async def list_system_images(db: Session = Depends(get_db)):
    """Liste toutes les images système"""
    system_images = db.query(SystemImage).all()
    return system_images



# ... (autres imports existants)

@router.post("/system-images/", 
            response_model=SystemImageResponse, 
            status_code=status.HTTP_201_CREATED,
            summary="Créer une nouvelle image système",
            description="Crée une nouvelle image système avec les détails fournis et une image optionnelle",
            response_description="L'image système créée")
async def create_system_image(
    name: str = Form(..., description="Nom de l'image système"),
    os_type: str = Form(..., description="Type de système d'exploitation (ex: ubuntu-22.04)"),
    version: str = Form(..., description="Version du système d'exploitation"),
    description: Optional[str] = Form(None, description="Description de l'image système"),
    image: Optional[UploadFile] = File(None, description="Fichier image optionnel à télécharger (PNG, JPG, JPEG)"),
    db: Session = Depends(get_db)
):
    """
    Crée une nouvelle image système avec les détails fournis et une image optionnelle.
    
    - **name**: Nom de l'image système
    - **os_type**: Type de système d'exploitation (ex: ubuntu-22.04)
    - **version**: Version du système d'exploitation
    - **description**: Description optionnelle de l'image
    - **image**: Fichier image optionnel (PNG, JPG, JPEG)
    """
    # Gérer l'upload d'image
    image_path = None
    if image and image.filename:
        # Vérifier le type de fichier
        allowed_extensions = {".png", ".jpg", ".jpeg"}
        file_extension = os.path.splitext(image.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Type de fichier non pris en charge. Utilisez un fichier {', '.join(allowed_extensions)}"
            )
        
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

@router.get("/system-images/{id}", response_model=SystemImageResponse)
async def get_system_image(id: int, db: Session = Depends(get_db)):
    """Obtient une image système par son ID"""
    system_image = db.query(SystemImage).filter(SystemImage.id == id).first()
    if system_image is None:
        raise HTTPException(status_code=404, detail="Image système non trouvée")
    return system_image

@router.put("/system-images/{id}", 
            response_model=SystemImageResponse,
            summary="Mettre à jour une image système",
            description="Met à jour les détails d'une image système existante et/ou son image",
            response_description="L'image système mise à jour")
async def update_system_image(
    id: int = Path(..., description="ID de l'image système à mettre à jour"),
    name: Optional[str] = Form(None, description="Nouveau nom de l'image système"),
    os_type: Optional[str] = Form(None, description="Nouveau type de système d'exploitation"),
    version: Optional[str] = Form(None, description="Nouvelle version du système"),
    description: Optional[str] = Form(None, description="Nouvelle description"),
    image: Optional[UploadFile] = File(None, description="Nouvelle image (optionnelle)"),
    db: Session = Depends(get_db)
):
    """
    Met à jour les détails d'une image système existante et/ou son image.
    
    - **id**: ID de l'image système à mettre à jour
    - **name**: Nouveau nom de l'image (optionnel)
    - **os_type**: Nouveau type de système (optionnel)
    - **version**: Nouvelle version (optionnelle)
    - **description**: Nouvelle description (optionnelle)
    - **image**: Nouvelle image (optionnelle)
    """
    system_image = db.query(SystemImage).filter(SystemImage.id == id).first()
    if system_image is None:
        raise HTTPException(status_code=404, detail="Image système non trouvée")
    
    # Gérer l'upload d'image
    old_image_path = system_image.image_path
    new_image_path = old_image_path
    
    if image and image.filename:
        # Vérifier le type de fichier
        allowed_extensions = {".png", ".jpg", ".jpeg"}
        file_extension = os.path.splitext(image.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Type de fichier non pris en charge. Utilisez un fichier {', '.join(allowed_extensions)}"
            )
            
        new_image_path = handle_image_upload(image)
        # Supprimer l'ancienne image si elle existe
        if old_image_path and os.path.exists(old_image_path):
            delete_image_file(old_image_path)
    elif image is not None and not image.filename:
        # Si un fichier vide est fourni, supprimer l'image existante
        new_image_path = None
        if old_image_path and os.path.exists(old_image_path):
            delete_image_file(old_image_path)
    
    # Mettre à jour uniquement les attributs fournis
    if name is not None:
        system_image.name = name
    if os_type is not None:
        system_image.os_type = os_type
    if version is not None:
        system_image.version = version
    if description is not None:
        system_image.description = description
    if new_image_path != old_image_path:  # Si une nouvelle image a été téléchargée
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

@router.delete("/system-images/{id}", status_code=status.HTTP_200_OK)
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

@router.get("/system-images/search/{name}", response_model=List[SystemImageResponse])
async def search_system_images(name: str, db: Session = Depends(get_db)):
    """Recherche des images système par nom"""
    system_images = db.query(SystemImage).filter(SystemImage.name.like(f"%{name}%")).all()
    return system_images

@router.get("/system-images/os-type/{os_type}", response_model=List[SystemImageResponse])
async def get_system_images_by_os_type(os_type: str, db: Session = Depends(get_db)):
    """Obtient les images système par type de système d'exploitation"""
    system_images = db.query(SystemImage).filter(SystemImage.os_type == os_type).all()
    return system_images
