#!/usr/bin/env python3
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, func, Enum, Float
from pydantic import BaseModel
from database import Base
from datetime import datetime


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

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'os_type': self.os_type,
            'version': self.version,
            'description': self.description,
            'image_path': self.image_path,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


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
        from_attributes = True