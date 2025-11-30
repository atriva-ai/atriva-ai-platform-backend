from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.zone import Zone
from app.db.schemas.zone import ZoneCreate, ZoneUpdate, Zone as ZoneSchema

def get_zone(db: Session, zone_id: int) -> Optional[Zone]:
    return db.query(Zone).filter(Zone.id == zone_id).first()

def get_zone_by_name(db: Session, name: str) -> Optional[Zone]:
    return db.query(Zone).filter(Zone.name == name).first()

def get_all_zones(db: Session, skip: int = 0, limit: int = 100) -> List[Zone]:
    return db.query(Zone).offset(skip).limit(limit).all()

def get_zones(db: Session, skip: int = 0, limit: int = 100) -> List[Zone]:
    return db.query(Zone).offset(skip).limit(limit).all()

def get_zones_by_camera(db: Session, camera_id: int) -> List[Zone]:
    return db.query(Zone).filter(Zone.camera_id == camera_id).all()

def create_zone(db: Session, zone: ZoneCreate) -> Zone:
    db_zone = Zone(**zone.model_dump())
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

def update_zone(
    db: Session, 
    zone_id: int, 
    zone: ZoneUpdate
) -> Optional[Zone]:
    db_zone = get_zone(db, zone_id)
    if db_zone:
        update_data = zone.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_zone, field, value)
        db.commit()
        db.refresh(db_zone)
    return db_zone

def update_zone_alt(db: Session, zone_id: int, zone_update: ZoneUpdate) -> Optional[Zone]:
    db_zone = get_zone(db, zone_id)
    if not db_zone:
        return None
    
    update_data = zone_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_zone, field, value)
    
    db.commit()
    db.refresh(db_zone)
    return db_zone

def delete_zone(db: Session, zone_id: int) -> bool:
    db_zone = get_zone(db, zone_id)
    if db_zone:
        db.delete(db_zone)
        db.commit()
        return True
    return False

def toggle_zone_active(db: Session, zone_id: int) -> Optional[Zone]:
    db_zone = get_zone(db, zone_id)
    if db_zone:
        db_zone.is_active = not db_zone.is_active
        db.commit()
        db.refresh(db_zone)
    return db_zone
