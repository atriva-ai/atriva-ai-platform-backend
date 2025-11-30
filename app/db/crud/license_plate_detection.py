from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.license_plate_detection import LicensePlateDetection
from app.db.schemas.license_plate_detection import LicensePlateDetectionCreate, LicensePlateDetectionUpdate
from datetime import datetime

def create_license_plate_detection(db: Session, detection: LicensePlateDetectionCreate) -> LicensePlateDetection:
    """Create a new license plate detection record"""
    db_detection = LicensePlateDetection(**detection.dict())
    db.add(db_detection)
    db.commit()
    db.refresh(db_detection)
    return db_detection

def get_license_plate_detection(db: Session, detection_id: int) -> Optional[LicensePlateDetection]:
    """Get a license plate detection by ID"""
    return db.query(LicensePlateDetection).filter(LicensePlateDetection.id == detection_id).first()

def get_license_plate_detections(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    source_type: Optional[str] = None,
    plate_number: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[LicensePlateDetection]:
    """Get license plate detections with optional filters"""
    query = db.query(LicensePlateDetection)
    
    if source_type:
        query = query.filter(LicensePlateDetection.source_type == source_type)
    if plate_number:
        query = query.filter(LicensePlateDetection.plate_number.ilike(f"%{plate_number}%"))
    if is_active is not None:
        query = query.filter(LicensePlateDetection.is_active == is_active)
    
    return query.order_by(LicensePlateDetection.detected_at.desc()).offset(skip).limit(limit).all()

def get_detections_by_plate_number(db: Session, plate_number: str) -> List[LicensePlateDetection]:
    """Get all detections for a specific license plate number"""
    return db.query(LicensePlateDetection).filter(
        LicensePlateDetection.plate_number == plate_number,
        LicensePlateDetection.is_active == True
    ).order_by(LicensePlateDetection.detected_at.desc()).all()

def get_detections_by_source(db: Session, source_type: str, source_id: Optional[int] = None) -> List[LicensePlateDetection]:
    """Get detections by source type and optionally source ID"""
    query = db.query(LicensePlateDetection).filter(LicensePlateDetection.source_type == source_type)
    
    if source_id is not None:
        query = query.filter(LicensePlateDetection.source_id == source_id)
    
    return query.filter(LicensePlateDetection.is_active == True).order_by(LicensePlateDetection.detected_at.desc()).all()

def update_license_plate_detection(db: Session, detection_id: int, detection_update: LicensePlateDetectionUpdate) -> Optional[LicensePlateDetection]:
    """Update a license plate detection"""
    db_detection = db.query(LicensePlateDetection).filter(LicensePlateDetection.id == detection_id).first()
    if not db_detection:
        return None
    
    update_data = detection_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_detection, field, value)
    
    db_detection.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_detection)
    return db_detection

def delete_license_plate_detection(db: Session, detection_id: int) -> bool:
    """Soft delete a license plate detection (set is_active to False)"""
    db_detection = db.query(LicensePlateDetection).filter(LicensePlateDetection.id == detection_id).first()
    if not db_detection:
        return False
    
    db_detection.is_active = False
    db_detection.updated_at = datetime.utcnow()
    db.commit()
    return True

def get_repeated_plates(db: Session, timeframe_hours: int = 24) -> List[dict]:
    """Get license plates that appear multiple times within a timeframe"""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
    
    # Get all active detections within timeframe
    detections = db.query(LicensePlateDetection).filter(
        LicensePlateDetection.is_active == True,
        LicensePlateDetection.detected_at >= cutoff_time
    ).all()
    
    # Group by plate number
    plate_groups = {}
    for detection in detections:
        plate_number = detection.plate_number
        if plate_number not in plate_groups:
            plate_groups[plate_number] = []
        plate_groups[plate_number].append(detection)
    
    # Filter for plates with multiple detections
    repeated_plates = []
    for plate_number, plate_detections in plate_groups.items():
        if len(plate_detections) > 1:
            repeated_plates.append({
                "plate_number": plate_number,
                "count": len(plate_detections),
                "detections": plate_detections
            })
    
    # Sort by count (most repeated first)
    repeated_plates.sort(key=lambda x: x["count"], reverse=True)
    return repeated_plates
