from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.db.models.entry_exit_event import EntryExitEvent
from app.db.schemas.entry_exit_event import EntryExitEventCreate

def create_entry_exit_event(db: Session, event: EntryExitEventCreate) -> EntryExitEvent:
    """Create a new entry/exit event"""
    db_event = EntryExitEvent(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_entry_exit_events(
    db: Session,
    camera_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
) -> List[EntryExitEvent]:
    """Get entry/exit events with optional filters"""
    query = db.query(EntryExitEvent)
    
    if camera_id is not None:
        query = query.filter(EntryExitEvent.camera_id == camera_id)
    
    if start_time is not None:
        query = query.filter(EntryExitEvent.timestamp >= start_time)
    
    if end_time is not None:
        query = query.filter(EntryExitEvent.timestamp <= end_time)
    
    return query.order_by(EntryExitEvent.timestamp.desc()).offset(skip).limit(limit).all()

def get_entry_exit_event(db: Session, event_id: int) -> Optional[EntryExitEvent]:
    """Get a specific entry/exit event by ID"""
    return db.query(EntryExitEvent).filter(EntryExitEvent.id == event_id).first()

def delete_entry_exit_event(db: Session, event_id: int) -> bool:
    """Delete an entry/exit event"""
    db_event = get_entry_exit_event(db, event_id)
    if db_event:
        db.delete(db_event)
        db.commit()
        return True
    return False

def delete_entry_exit_events_by_camera(db: Session, camera_id: int) -> int:
    """Delete all entry/exit events for a camera. Returns the number of deleted events."""
    deleted_count = db.query(EntryExitEvent).filter(EntryExitEvent.camera_id == camera_id).delete()
    db.commit()
    return deleted_count

