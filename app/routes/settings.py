from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..db.models.settings import Settings
from ..db.schemas.settings import SettingsCreate, SettingsUpdate, SettingsResponse
from ..database import get_db, Base, engine

router = APIRouter()

# Ensure tables exist
Base.metadata.create_all(bind=engine)

@router.get("/", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    try:
        settings = db.query(Settings).first()
        if not settings:
            # Create default settings if none exist
            settings = Settings(store_name="Default Store")
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/", response_model=SettingsResponse)
def update_settings(settings_data: SettingsUpdate, db: Session = Depends(get_db)):
    try:
        settings = db.query(Settings).first()
        if not settings:
            # If no settings exist, create new with defaults
            settings = Settings(store_name="Default Store")
            db.add(settings)
        
        # Update only the fields that were provided
        update_data = settings_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:  # Only update if value is not None
                setattr(settings, key, value)
        
        db.commit()
        db.refresh(settings)
        return settings
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/", response_model=SettingsResponse)
def create_settings(settings_data: SettingsCreate, db: Session = Depends(get_db)):
    try:
        existing_settings = db.query(Settings).first()
        if existing_settings:
            raise HTTPException(status_code=400, detail="Settings already exist. Use PUT to update.")
        
        settings = Settings(**settings_data.model_dump())
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}") 