from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.db.models.alert_engine import AlertEngine
from app.db.models.camera import Camera
from app.db.schemas.alert_engine import AlertEngineCreate, AlertEngineUpdate
from app.db.models.camera_alert_engine import camera_alert_engines

def get_alert_engine(db: Session, alert_engine_id: int) -> Optional[AlertEngine]:
    return db.query(AlertEngine).filter(AlertEngine.id == alert_engine_id).first()

def get_alert_engine_by_name(db: Session, name: str) -> Optional[AlertEngine]:
    return db.query(AlertEngine).filter(AlertEngine.name == name).first()

def get_all_alert_engines(db: Session, skip: int = 0, limit: int = 100) -> List[AlertEngine]:
    return db.query(AlertEngine).offset(skip).limit(limit).all()

def get_alert_engines(db: Session, skip: int = 0, limit: int = 100) -> List[AlertEngine]:
    return db.query(AlertEngine).offset(skip).limit(limit).all()

def get_camera_alert_engines(db: Session, camera_id: int) -> List[AlertEngine]:
    return db.query(AlertEngine).join(camera_alert_engines).filter(camera_alert_engines.c.camera_id == camera_id).all()

def get_cameras_by_alert_engine(db: Session, alert_engine_id: int) -> List[Camera]:
    return db.query(Camera).join(camera_alert_engines).filter(camera_alert_engines.c.alert_engine_id == alert_engine_id).all()

def create_alert_engine(db: Session, alert_engine: AlertEngineCreate) -> AlertEngine:
    db_alert_engine = AlertEngine(**alert_engine.model_dump())
    db.add(db_alert_engine)
    db.commit()
    db.refresh(db_alert_engine)
    return db_alert_engine

def update_alert_engine(db: Session, alert_engine_id: int, alert_engine: AlertEngineUpdate) -> Optional[AlertEngine]:
    db_alert_engine = get_alert_engine(db, alert_engine_id)
    if db_alert_engine:
        update_data = alert_engine.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_alert_engine, field, value)
        db.commit()
        db.refresh(db_alert_engine)
    return db_alert_engine

def delete_alert_engine(db: Session, alert_engine_id: int) -> bool:
    db_alert_engine = get_alert_engine(db, alert_engine_id)
    if db_alert_engine:
        db.delete(db_alert_engine)
        db.commit()
        return True
    return False

def add_alert_engine_to_camera(db: Session, camera_id: int, alert_engine_id: int) -> bool:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    alert_engine = get_alert_engine(db, alert_engine_id)
    
    if camera and alert_engine:
        camera.alert_engines.append(alert_engine)
        db.commit()
        return True
    return False

def remove_alert_engine_from_camera(db: Session, camera_id: int, alert_engine_id: int) -> bool:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    alert_engine = get_alert_engine(db, alert_engine_id)
    
    if camera and alert_engine:
        if alert_engine in camera.alert_engines:
            camera.alert_engines.remove(alert_engine)
            db.commit()
            return True
    return False

def toggle_alert_engine_active(db: Session, alert_engine_id: int) -> Optional[AlertEngine]:
    db_alert_engine = get_alert_engine(db, alert_engine_id)
    if db_alert_engine:
        db_alert_engine.is_active = not db_alert_engine.is_active
        db.commit()
        db.refresh(db_alert_engine)
    return db_alert_engine 