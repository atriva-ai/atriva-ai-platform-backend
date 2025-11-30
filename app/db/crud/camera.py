from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models.camera import Camera
from app.db.schemas.camera import CameraCreate, CameraUpdate

def create_camera(db: Session, camera: CameraCreate) -> Camera:
    # Exclude zone_ids from the model dump since it's not a field in the Camera model
    camera_data = camera.model_dump(exclude={'zone_ids'})
    print(f"🔍 CRUD DEBUG: camera_data before creating: {camera_data}")
    db_camera = Camera(**camera_data)
    print(f"🔍 CRUD DEBUG: db_camera before commit: {db_camera}")
    print(f"🔍 CRUD DEBUG: db_camera.is_active before commit: {db_camera.is_active}")
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    
    print(f"🔍 CRUD DEBUG: db_camera after commit: {db_camera}")
    print(f"🔍 CRUD DEBUG: db_camera.is_active after commit: {db_camera.is_active}")
    print(f"🔍 CRUD DEBUG: db_camera.vehicle_tracking_enabled after commit: {db_camera.vehicle_tracking_enabled}")
    print(f"🔍 CRUD DEBUG: db_camera.vehicle_tracking_enabled type after commit: {type(db_camera.vehicle_tracking_enabled)}")
    
    return db_camera

def get_cameras(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None
) -> List[Camera]:
    query = db.query(Camera)
    if is_active is not None:
        query = query.filter(Camera.is_active == is_active)
    return query.offset(skip).limit(limit).all()

def get_camera(db: Session, camera_id: int) -> Optional[Camera]:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    return camera

def update_camera(
    db: Session, 
    camera_id: int, 
    camera_update: CameraUpdate
) -> Optional[Camera]:
    print(f"🔍 CRUD UPDATE: Updating camera {camera_id}")
    
    db_camera = get_camera(db, camera_id)
    if not db_camera:
        print(f"❌ CRUD UPDATE: Camera {camera_id} not found")
        return None

    update_data = camera_update.model_dump(exclude_unset=True, exclude={'zone_ids'})
    print(f"🔍 CRUD UPDATE: Update data for camera {camera_id}: {update_data}")
    
    if 'vehicle_tracking_enabled' in update_data:
        print(f"🔍 CRUD UPDATE: vehicle_tracking_enabled in update_data: {update_data['vehicle_tracking_enabled']}")
        print(f"🔍 CRUD UPDATE: vehicle_tracking_enabled type: {type(update_data['vehicle_tracking_enabled'])}")
    
    for field, value in update_data.items():
        setattr(db_camera, field, value)

    db.commit()
    db.refresh(db_camera)
    
    print(f"🔍 CRUD UPDATE: Camera {camera_id} vehicle_tracking_enabled after commit: {db_camera.vehicle_tracking_enabled}")
    print(f"🔍 CRUD UPDATE: Camera {camera_id} vehicle_tracking_enabled type after commit: {type(db_camera.vehicle_tracking_enabled)}")
    
    return db_camera

def delete_camera(db: Session, camera_id: int) -> bool:
    db_camera = get_camera(db, camera_id)
    if not db_camera:
        return False

    db.delete(db_camera)
    db.commit()
    return True

# crud/camera.py
def update_camera_analytics(db: Session, camera_id: int, analytics_config: dict):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if db_camera:
        db_camera.analytics_config = analytics_config
        db.commit()
        db.refresh(db_camera)
    return db_camera

def get_cameras_count(db: Session, is_active: Optional[bool] = None) -> int:
    query = db.query(Camera)
    if is_active is not None:
        query = query.filter(Camera.is_active == is_active)
    return query.count()
