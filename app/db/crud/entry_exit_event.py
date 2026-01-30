from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from datetime import datetime, date
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

def get_entry_exit_counts_by_camera(
    db: Session,
    target_date: Optional[date] = None,
    camera_id: Optional[int] = None
) -> List[Dict]:
    """
    Get aggregated entrance/exit counts grouped by camera.
    
    Args:
        db: Database session
        target_date: Date to filter by (defaults to today in UTC)
        camera_id: Optional camera ID to filter by
    
    Returns:
        List of dicts with keys: camera_id, enter_count, exit_count, total_count
    """
    # Default to today if no date provided
    if target_date is None:
        target_date = datetime.utcnow().date()
    
    # Start and end of the target date (UTC)
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    # Base query
    query = db.query(
        EntryExitEvent.camera_id,
        EntryExitEvent.event,
        func.count(EntryExitEvent.id).label('count')
    ).filter(
        EntryExitEvent.timestamp >= start_datetime,
        EntryExitEvent.timestamp <= end_datetime
    )
    
    # Filter by camera if provided
    if camera_id is not None:
        query = query.filter(EntryExitEvent.camera_id == camera_id)
    
    # Group by camera_id and event type
    query = query.group_by(EntryExitEvent.camera_id, EntryExitEvent.event)
    
    results = query.all()
    
    # Aggregate results by camera_id
    camera_counts: Dict[int, Dict] = {}
    
    for camera_id, event_type, count in results:
        if camera_id not in camera_counts:
            camera_counts[camera_id] = {
                'camera_id': camera_id,
                'enter_count': 0,
                'exit_count': 0,
                'total_count': 0
            }
        
        if event_type == 'enter':
            camera_counts[camera_id]['enter_count'] = count
        elif event_type == 'exit':
            camera_counts[camera_id]['exit_count'] = count
        
        camera_counts[camera_id]['total_count'] += count
    
    # Convert to list and sort by camera_id
    return sorted(camera_counts.values(), key=lambda x: x['camera_id'])

