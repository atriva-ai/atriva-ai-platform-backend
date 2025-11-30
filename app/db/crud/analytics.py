from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.db.models.analytics import Analytics
from app.db.models.camera import Camera
from app.db.schemas.analytics import AnalyticsCreate, AnalyticsUpdate

def get_analytics(db: Session, analytics_id: int) -> Optional[Analytics]:
    return db.query(Analytics).filter(Analytics.id == analytics_id).first()

def get_analytics_by_type(db: Session, analytics_type: str) -> Optional[Analytics]:
    return db.query(Analytics).filter(Analytics.type == analytics_type).first()

def get_all_analytics(db: Session, skip: int = 0, limit: int = 100) -> List[Analytics]:
    return db.query(Analytics).offset(skip).limit(limit).all()

def create_analytics(db: Session, analytics: AnalyticsCreate) -> Analytics:
    db_analytics = Analytics(**analytics.model_dump())
    db.add(db_analytics)
    db.commit()
    db.refresh(db_analytics)
    return db_analytics

def update_analytics(
    db: Session, 
    analytics_id: int, 
    analytics: AnalyticsUpdate
) -> Optional[Analytics]:
    db_analytics = get_analytics(db, analytics_id)
    if db_analytics:
        update_data = analytics.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_analytics, field, value)
        db.commit()
        db.refresh(db_analytics)
    return db_analytics

def delete_analytics(db: Session, analytics_id: int) -> bool:
    db_analytics = get_analytics(db, analytics_id)
    if db_analytics:
        db.delete(db_analytics)
        db.commit()
        return True
    return False

def get_camera_analytics(db: Session, camera_id: int) -> List[Analytics]:
    return db.query(Analytics).join(
        Analytics.cameras
    ).filter(
        Analytics.cameras.any(id=camera_id)
    ).all()

def add_analytics_to_camera(
    db: Session, 
    camera_id: int, 
    analytics_id: int
) -> bool:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    analytics = get_analytics(db, analytics_id)
    
    if camera and analytics:
        camera.analytics.append(analytics)
        db.commit()
        return True
    return False

def remove_analytics_from_camera(
    db: Session, 
    camera_id: int, 
    analytics_id: int
) -> bool:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    analytics = get_analytics(db, analytics_id)
    
    if camera and analytics:
        camera.analytics.remove(analytics)
        db.commit()
        return True
    return False 