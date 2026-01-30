"""
Entrance/Exit Analytics Routes

API endpoints for configuring and querying entrance/exit analytics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from app.database import get_db
from app.db.crud import analytics as analytics_crud
from app.db.crud import entry_exit_event as event_crud
from app.db.schemas.entry_exit_event import EntryExitEvent
from app.db.schemas.analytics import AnalyticsUpdate
from app.constants.analytics import AnalyticsType
import threading
import time
import requests
import os
from app.services.entrance_exit_engine import process_person_centroid, clear_track_position
from app.db.crud import camera as camera_crud

router = APIRouter(
    prefix="/api/v1/entrance-exit",
    tags=["entrance-exit"]
)

AI_INFERENCE_URL = os.getenv("AI_INFERENCE_URL", "http://ai_inference:8001")

# Thread manager: {camera_id: thread}
entrance_polling_threads = {}
# Thread control: {camera_id: should_stop}
thread_control = {}


def stop_entrance_polling(camera_id: int):
    """Stop the background polling thread for a camera"""
    if camera_id in entrance_polling_threads:
        print(f"⏸️ Stopping entrance/exit polling for camera {camera_id}")
        thread_control[camera_id] = True
        del entrance_polling_threads[camera_id]
    elif camera_id in thread_control:
        # Clean up thread control even if thread doesn't exist
        thread_control[camera_id] = True


def start_entrance_polling(camera_id: int, db_session_factory):
    """Start a background thread to poll AI inference for person detections and process entrance/exit events"""
    def polling_loop():
        session = db_session_factory()
        try:
            # Get entrance analytics config for this camera
            camera_analytics = analytics_crud.get_camera_analytics(session, camera_id)
            entrance_analytics = None
            for analytics in camera_analytics:
                if analytics.type == AnalyticsType.ENTRANCE and analytics.is_active:
                    entrance_analytics = analytics
                    break
            
            if not entrance_analytics:
                print(f"No active entrance analytics found for camera {camera_id}")
                return
            
            config = entrance_analytics.config or {}
            if not config.get("enabled", False):
                print(f"Entrance analytics not enabled for camera {camera_id}")
                return
            
            line_config = config.get("line", {})
            if not line_config or not all(k in line_config for k in ["x1", "y1", "x2", "y2"]):
                print(f"Invalid line configuration for camera {camera_id}")
                return
            
            direction_filter = config.get("direction", "both")
            entrance_side_point = config.get("entrance_side")  # Optional: {'x': float, 'y': float}
            
            print(f"🚀 Starting entrance/exit polling for camera {camera_id} with line: {line_config}")
            
            # Poll for person detections
            while camera_id not in thread_control or not thread_control[camera_id]:
                try:
                    # Get tracked person detections from AI inference service
                    resp = requests.get(
                        f"{AI_INFERENCE_URL}/shared/cameras/{camera_id}/detections/latest",
                        params={"object_filter": "person"},
                        timeout=5.0
                    )
                    
                    if resp.ok:
                        result = resp.json()
                        detections = result.get("detections", [])
                        
                        if len(detections) > 0:
                            print(f"📊 Received {len(detections)} person detections for camera {camera_id}")
                        
                        # Process each detection
                        for det in detections:
                            track_id = det.get("track_id")
                            bbox = det.get("bbox", [])
                            
                            if track_id is None or len(bbox) != 4:
                                continue
                            
                            # Calculate centroid from bbox [x1, y1, x2, y2]
                            x1, y1, x2, y2 = bbox
                            centroid_x = (x1 + x2) / 2.0
                            centroid_y = (y1 + y2) / 2.0
                            
                            # Get timestamp
                            timestamp = det.get("timestamp")
                            if timestamp is None:
                                timestamp = time.time()
                            
                            # Process centroid event
                            event = process_person_centroid(
                                session,
                                camera_id,
                                track_id,
                                centroid_x,
                                centroid_y,
                                line_config,
                                direction_filter,
                                timestamp,
                                entrance_side_point
                            )
                            if event:
                                print(f"✅ Processed {event['event']} event for track {track_id} on camera {camera_id}")
                    
                    time.sleep(1)  # Poll every second
                    
                except requests.exceptions.RequestException as e:
                    print(f"⚠️ Network error fetching detections for camera {camera_id}: {e}")
                    time.sleep(1)
                except Exception as e:
                    print(f"❌ Error in entrance/exit polling for camera {camera_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)
            
            print(f"⏸️ Entrance/exit polling stopped for camera {camera_id}")
        finally:
            session.close()
            if camera_id in thread_control:
                del thread_control[camera_id]
    
    if camera_id in entrance_polling_threads:
        print(f"Entrance/exit polling already running for camera {camera_id}")
        return
    
    thread_control[camera_id] = False
    thread = threading.Thread(target=polling_loop, daemon=True)
    entrance_polling_threads[camera_id] = thread
    thread.start()


@router.get("/config/{camera_id}")
def get_entrance_config(camera_id: int, db: Session = Depends(get_db)):
    """Get entrance/exit configuration for a camera"""
    camera_analytics = analytics_crud.get_camera_analytics(db, camera_id)
    entrance_analytics = None
    for analytics in camera_analytics:
        if analytics.type == AnalyticsType.ENTRANCE:
            entrance_analytics = analytics
            break
    
    if not entrance_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrance analytics not configured for this camera"
        )
    
    config = entrance_analytics.config or {}
    return {
        "camera_id": camera_id,
        "enabled": config.get("enabled", False),
        "line": config.get("line", {}),
        "direction": config.get("direction", "both"),
        "is_active": entrance_analytics.is_active
    }


@router.put("/config/{camera_id}")
def update_entrance_config(
    camera_id: int,
    enabled: Optional[bool] = None,
    line: Optional[dict] = None,
    direction: Optional[str] = None,
    entrance_side: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    """Update entrance/exit configuration for a camera"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    # Get or create entrance analytics
    camera_analytics = analytics_crud.get_camera_analytics(db, camera_id)
    entrance_analytics = None
    for analytics in camera_analytics:
        if analytics.type == AnalyticsType.ENTRANCE:
            entrance_analytics = analytics
            break
    
    if not entrance_analytics:
        # Create new entrance analytics
        from app.db.schemas.analytics import AnalyticsCreate
        from app.constants.analytics import AnalyticsConfig
        
        entrance_config = AnalyticsConfig.ENTRANCE["default_config"].copy()
        # If enabled is explicitly set, use it; otherwise default to True if line is provided
        if enabled is not None:
            entrance_config["enabled"] = enabled
        elif line is not None:
            entrance_config["enabled"] = True  # Auto-enable if line is provided
        if line is not None:
            entrance_config["line"] = line
        if direction is not None:
            entrance_config["direction"] = direction
        if entrance_side is not None:
            entrance_config["entrance_side"] = entrance_side
        
        print(f"🔧 Creating entrance analytics for camera {camera_id} with config: {entrance_config}")
        
        new_analytics = AnalyticsCreate(
            name="Entrance / Exit Analytics",
            type=AnalyticsType.ENTRANCE,
            config=entrance_config,
            is_active=True
        )
        entrance_analytics = analytics_crud.create_analytics(db, new_analytics)
        analytics_crud.add_analytics_to_camera(db, camera_id, entrance_analytics.id)
        print(f"✅ Created entrance analytics (id={entrance_analytics.id}) for camera {camera_id}")
    else:
        # Update existing analytics
        config = entrance_analytics.config or {}
        
        # Fix malformed config structure (if enabled/direction are nested in line)
        if isinstance(config.get("line"), dict):
            line_obj = config["line"]
            # If line contains enabled/direction, extract them
            if "enabled" in line_obj:
                if enabled is None:
                    enabled = line_obj.pop("enabled")
            if "direction" in line_obj:
                if direction is None:
                    direction = line_obj.pop("direction")
            # If line contains another "line" key, use that
            if "line" in line_obj:
                if line is None:
                    line = line_obj.pop("line")
                # Remove the outer line wrapper
                config["line"] = line_obj.get("line", line_obj)
        
        # Handle enabled flag (after extracting from nested structure)
        if enabled is not None:
            config["enabled"] = enabled
        elif line is not None:
            # Auto-enable if line is being set and enabled wasn't explicitly set
            config["enabled"] = True
        elif not config.get("enabled", False):
            # If enabled wasn't set and no line provided, ensure it's at least False
            config["enabled"] = False
        
        # Handle line config
        if line is not None:
            config["line"] = line
        
        # Handle direction
        if direction is not None:
            config["direction"] = direction
        
        # Handle entrance_side
        if entrance_side is not None:
            config["entrance_side"] = entrance_side
        
        # Clean up config structure - ensure enabled/direction are at top level, not nested
        if "line" in config and isinstance(config["line"], dict):
            # If line is a dict, make sure it only contains x1, y1, x2, y2
            line_data = config["line"]
            if all(k in line_data for k in ["x1", "y1", "x2", "y2"]):
                # This is a valid line, keep it
                pass
            else:
                # Line might be malformed, try to extract valid line data
                if "line" in line_data and isinstance(line_data["line"], dict):
                    config["line"] = line_data["line"]
        
        # Ensure enabled is explicitly set in config
        if "enabled" not in config:
            config["enabled"] = True if line is not None else False
        
        print(f"🔧 Updating entrance analytics for camera {camera_id} with cleaned config: {config}")
        print(f"🔍 Config keys: {list(config.keys())}, enabled value: {config.get('enabled')}")
        
        # Create update with config explicitly set
        update = AnalyticsUpdate(config=config)
        print(f"🔍 Creating AnalyticsUpdate with config: {config}")
        update_data = update.model_dump(exclude_unset=False)  # Don't exclude unset, include everything
        print(f"🔍 Update data being sent: {update_data}")
        
        updated_analytics = analytics_crud.update_analytics(db, entrance_analytics.id, update)
        
        # Force refresh to get latest data from database
        db.refresh(updated_analytics)
        entrance_analytics = updated_analytics
        
        # Verify the config was saved correctly by querying directly from DB
        final_config = entrance_analytics.config or {}
        print(f"✅ After update, config is: {final_config}, enabled={final_config.get('enabled')}")
        print(f"🔍 Final config keys: {list(final_config.keys()) if final_config else 'empty'}")
        
        # Double-check by re-querying from database
        db.expire_all()  # Expire all cached objects to force fresh query
        fresh_analytics = analytics_crud.get_analytics(db, entrance_analytics.id)
        if fresh_analytics:
            fresh_config = fresh_analytics.config or {}
            print(f"🔍 Fresh query from DB: config={fresh_config}, enabled={fresh_config.get('enabled')}")
            entrance_analytics = fresh_analytics
            final_config = fresh_config
    
    # Refresh to get latest config from database
    db.refresh(entrance_analytics)
    
    # Start/stop polling based on enabled status
    final_config = entrance_analytics.config or {}
    print(f"🔍 Entrance config check for camera {camera_id}: enabled={final_config.get('enabled', False)}, is_active={entrance_analytics.is_active}, config={final_config}")
    
    if final_config.get("enabled", False) and entrance_analytics.is_active:
        # Ensure person detection is enabled for the camera
        if not camera.person_detection_enabled:
            from app.db.schemas.camera import CameraUpdate
            camera_update = CameraUpdate(person_detection_enabled=True)
            camera_crud.update_camera(db, camera_id, camera_update)
            print(f"✅ Enabled person detection for camera {camera_id} (required for entrance/exit analytics)")
        
        # Ensure AI inference is running with person tracking
        # The entrance polling will request detections with object_filter="person" which enables tracking
        try:
            inference_check = requests.get(
                f"{AI_INFERENCE_URL}/inference/continuous/status",
                params={"camera_id": str(camera_id)},
                timeout=2.0
            )
            if not (inference_check.ok and inference_check.json().get("running", False)):
                # Get FPS from settings
                from app.db.models.settings import Settings
                settings = db.query(Settings).first()
                inference_fps = 5.0  # Default
                if settings and hasattr(settings, 'ai_inference_fps'):
                    inference_fps = settings.ai_inference_fps
                
                # Start inference with person tracking
                inference_start = requests.post(
                    f"{AI_INFERENCE_URL}/inference/continuous/start",
                    params={
                        "camera_id": str(camera_id),
                        "model_name": "yolov8n",
                        "accelerator": "cpu32",
                        "object_filter": "person",
                        "inference_fps": inference_fps
                    },
                    timeout=5.0
                )
                if inference_start.ok:
                    print(f"✅ Started AI inference with person tracking for camera {camera_id}")
                else:
                    print(f"⚠️ Failed to start AI inference for camera {camera_id}: {inference_start.status_code}")
        except Exception as e:
            print(f"⚠️ Could not verify/start AI inference for camera {camera_id}: {e}")
        
        from app.database import SessionLocal
        start_entrance_polling(camera_id, SessionLocal)
        print(f"✅ Started entrance/exit polling for camera {camera_id}")
    else:
        print(f"⚠️ Not starting polling: enabled={final_config.get('enabled', False)}, is_active={entrance_analytics.is_active}")
        stop_entrance_polling(camera_id)
        print(f"⏸️ Stopped entrance/exit polling for camera {camera_id}")
    
    return {
        "camera_id": camera_id,
        "enabled": final_config.get("enabled", False),
        "line": final_config.get("line", {}),
        "direction": final_config.get("direction", "both")
    }


@router.get("/events", response_model=List[EntryExitEvent])
def get_entrance_exit_events(
    camera_id: Optional[int] = Query(None, description="Filter by camera ID"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get entrance/exit events with optional filters"""
    events = event_crud.get_entry_exit_events(
        db,
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit
    )
    return events


@router.post("/camera/{camera_id}/start")
def start_entrance_tracking(camera_id: int, db: Session = Depends(get_db)):
    """Start entrance/exit tracking for a camera"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found"
        )
    
    # Get entrance analytics
    camera_analytics = analytics_crud.get_camera_analytics(db, camera_id)
    entrance_analytics = None
    for analytics in camera_analytics:
        if analytics.type == AnalyticsType.ENTRANCE:
            entrance_analytics = analytics
            break
    
    if not entrance_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrance analytics not configured for this camera"
        )
    
    config = entrance_analytics.config or {}
    if not config.get("enabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Entrance analytics is not enabled for this camera"
        )
    
    from app.database import SessionLocal
    start_entrance_polling(camera_id, SessionLocal)
    return {"message": f"Entrance/exit tracking started for camera {camera_id}"}


@router.post("/camera/{camera_id}/stop")
def stop_entrance_tracking(camera_id: int):
    """Stop entrance/exit tracking for a camera"""
    stop_entrance_polling(camera_id)
    return {"message": f"Entrance/exit tracking stopped for camera {camera_id}"}


@router.get("/camera/{camera_id}/status")
def get_entrance_tracking_status(camera_id: int, db: Session = Depends(get_db)):
    """Get the status of entrance/exit tracking for a camera"""
    is_running = camera_id in entrance_polling_threads
    thread = entrance_polling_threads.get(camera_id)
    is_alive = thread.is_alive() if thread else False
    
    # Get analytics config
    camera_analytics = analytics_crud.get_camera_analytics(db, camera_id)
    entrance_analytics = None
    for analytics in camera_analytics:
        if analytics.type == AnalyticsType.ENTRANCE:
            entrance_analytics = analytics
            break
    
    config = entrance_analytics.config if entrance_analytics else {}
    
    return {
        "camera_id": camera_id,
        "polling_running": is_running,
        "thread_alive": is_alive,
        "has_entrance_analytics": entrance_analytics is not None,
        "analytics_active": entrance_analytics.is_active if entrance_analytics else False,
        "enabled": config.get("enabled", False) if config else False,
        "has_line": bool(config.get("line", {}).get("x1")) if config else False,
        "line_config": config.get("line", {}) if config else {}
    }


@router.get("/counts")
def get_entrance_exit_counts(
    target_date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    camera_id: Optional[int] = Query(None, description="Filter by camera ID"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated entrance/exit counts by camera for a specific date.
    
    Returns counts grouped by camera with enter_count, exit_count, and total_count.
    """
    # Parse target_date if provided
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Get counts from database
    counts = event_crud.get_entry_exit_counts_by_camera(
        db=db,
        target_date=parsed_date,
        camera_id=camera_id
    )
    
    # Enrich with camera names
    result = []
    for count_data in counts:
        camera = camera_crud.get_camera(db, count_data['camera_id'])
        result.append({
            **count_data,
            'camera_name': camera.name if camera else f"Camera {count_data['camera_id']}",
            'camera_location': camera.location if camera else None
        })
    
    return {
        "date": (parsed_date or datetime.utcnow().date()).isoformat(),
        "counts": result
    }

