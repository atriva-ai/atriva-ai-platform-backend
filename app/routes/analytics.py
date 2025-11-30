from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.db.schemas.analytics import AnalyticsCreate, AnalyticsUpdate, Analytics, CameraAnalyticsCreate
from app.db.models.camera import Camera
from app.db.crud import analytics as analytics_crud
from app.constants.analytics import get_all_analytics_configs

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"]
)

@router.get("/types", response_model=dict)
def get_analytics_types():
    """Get all predefined analytics types and their configurations"""
    return get_all_analytics_configs()

@router.get("/", response_model=List[Analytics])
def get_all_analytics(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all analytics configurations"""
    return analytics_crud.get_all_analytics(db, skip=skip, limit=limit)

@router.post("/", response_model=Analytics, status_code=status.HTTP_201_CREATED)
def create_analytics(
    analytics: AnalyticsCreate,
    db: Session = Depends(get_db)
):
    """Create a new analytics configuration"""
    return analytics_crud.create_analytics(db, analytics)

@router.get("/{analytics_id}", response_model=Analytics)
def get_analytics(
    analytics_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific analytics configuration"""
    db_analytics = analytics_crud.get_analytics(db, analytics_id)
    if db_analytics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics configuration not found"
        )
    return db_analytics

@router.put("/{analytics_id}", response_model=Analytics)
def update_analytics(
    analytics_id: int,
    analytics: AnalyticsUpdate,
    db: Session = Depends(get_db)
):
    """Update an analytics configuration"""
    db_analytics = analytics_crud.update_analytics(db, analytics_id, analytics)
    if db_analytics is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics configuration not found"
        )
    return db_analytics

@router.delete("/{analytics_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analytics(
    analytics_id: int,
    db: Session = Depends(get_db)
):
    """Delete an analytics configuration"""
    success = analytics_crud.delete_analytics(db, analytics_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics configuration not found"
        )
    return None

@router.get("/camera/{camera_id}", response_model=List[Analytics])
def get_camera_analytics(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """Get all analytics configurations for a specific camera"""
    return analytics_crud.get_camera_analytics(db, camera_id)

@router.post("/camera", status_code=status.HTTP_201_CREATED)
def add_analytics_to_camera(
    camera_analytics: CameraAnalyticsCreate,
    db: Session = Depends(get_db)
):
    """Add an analytics configuration to a camera"""
    success = analytics_crud.add_analytics_to_camera(
        db, 
        camera_analytics.camera_id, 
        camera_analytics.analytics_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera or analytics configuration not found"
        )
    return {"message": "Analytics added to camera successfully"}

@router.delete("/camera/{camera_id}/{analytics_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_analytics_from_camera(
    camera_id: int,
    analytics_id: int,
    db: Session = Depends(get_db)
):
    """Remove an analytics configuration from a camera"""
    success = analytics_crud.remove_analytics_from_camera(db, camera_id, analytics_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera or analytics configuration not found"
        )
    return None 