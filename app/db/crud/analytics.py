from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
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
        # Use exclude_unset=False to ensure config is always included if provided
        update_data = analytics.model_dump(exclude_unset=False)
        print(f"🔍 CRUD: Raw update_data keys: {list(update_data.keys())}")
        print(f"🔍 CRUD: Config in update_data: {'config' in update_data}, value: {update_data.get('config')}")
        
        # Special handling for config - always update if provided (even if None)
        if "config" in update_data:
            new_config = update_data["config"]
            if new_config is not None:
                # Merge with existing config to preserve other fields
                existing_config = db_analytics.config or {}
                print(f"🔍 CRUD: Existing config: {existing_config}")
                print(f"🔍 CRUD: New config: {new_config}")
                # Merge configs (new values override existing)
                merged_config = {**existing_config, **new_config}
                print(f"🔍 CRUD: Merged config: {merged_config}")
                db_analytics.config = merged_config
                # CRITICAL: SQLAlchemy doesn't detect changes to nested JSON dicts
                # We must explicitly flag the column as modified
                flag_modified(db_analytics, "config")
                print(f"🔍 CRUD: Flagged config as modified")
            # Remove from update_data to avoid double-setting
            del update_data["config"]
        
        for field, value in update_data.items():
            if value is not None:  # Only update non-None fields
                setattr(db_analytics, field, value)
        
        db.commit()
        db.refresh(db_analytics)
        print(f"🔍 CRUD: After commit, config in DB: {db_analytics.config}")
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