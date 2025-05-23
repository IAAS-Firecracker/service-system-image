#!/usr/bin/env python3
from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Dépendance pour obtenir la session de base de données
def get_db():
    from database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modèle de réponse standardisée
class StandardResponse(BaseModel):
    statusCode: int
    message: str
    data: Optional[dict] = None
