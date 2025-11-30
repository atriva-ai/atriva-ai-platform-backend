from sqlalchemy.orm import Session
from typing import Optional, Any
from app.db.models.alert_event import AlertEvent
from app.db.schemas.alert_event import AlertEventCreate, AlertEventUpdate
from datetime import datetime

def create_alert_event(db: Session, event: AlertEventCreate) -> AlertEvent:
    db_event = AlertEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def update_alert_event(db: Session, event_id: int, update: AlertEventUpdate) -> Optional[AlertEvent]:
    db_event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if db_event:
        update_data = update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_event, field, value)
        db.commit()
        db.refresh(db_event)
    return db_event

def get_active_event(db: Session, camera_id: int, alert_type: str) -> Optional[AlertEvent]:
    return db.query(AlertEvent).filter(
        AlertEvent.camera_id == camera_id,
        AlertEvent.alert_type == alert_type,
        AlertEvent.end_time == None
    ).first()

def close_alert_event(db: Session, event_id: int, end_time: datetime) -> Optional[AlertEvent]:
    db_event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if db_event:
        db_event.end_time = end_time
        db.commit()
        db.refresh(db_event)
    return db_event 