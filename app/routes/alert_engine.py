from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.db.schemas.alert_engine import AlertEngineCreate, AlertEngineUpdate, AlertEngine, CameraAlertEngineCreate
from app.db.crud import alert_engine as alert_engine_crud
import threading
import time
import requests
import os
from app.db.crud import create_alert_event, update_alert_event, get_active_event, close_alert_event
from app.db.schemas.alert_event import AlertEventCreate, AlertEventUpdate
from datetime import datetime

router = APIRouter(
    prefix="/api/v1/alert-engines",
    tags=["alert-engines"]
)

# Thread manager: { (camera_id, model_name): thread }
alert_polling_threads = {}
# Thread control: { (camera_id, model_name): should_stop }
thread_control = {}

AI_INFERENCE_URL = os.getenv("AI_INFERENCE_URL", "http://ai_inference:8001")

def stop_alert_polling(camera_id: int, model_name: str):
    """Stop the background polling thread for a camera/model combination."""
    thread_key = (camera_id, model_name)
    if thread_key in alert_polling_threads:
        print(f"Stopping polling for camera {camera_id}, model {model_name}")
        # Mark thread for stopping
        thread_control[thread_key] = True
        # Remove from thread manager - the thread will exit naturally
        del alert_polling_threads[thread_key]

# --- Thread logic ---
def start_alert_polling(camera_id: int, model_name: str, alert_type: str, db_session_factory):
    """Start a background thread to poll AI inference for alerts."""
    def polling_loop():
        session = db_session_factory()
        thread_key = (camera_id, model_name)
        try:
            # 1. Ensure model is loaded
            resp = requests.get(f"{AI_INFERENCE_URL}/model/info")
            loaded = False
            if resp.ok:
                info = resp.json()
                loaded = model_name in info.get("models", [])
            if not loaded:
                load_resp = requests.post(f"{AI_INFERENCE_URL}/model/load", params={"model_name": model_name, "accelerator": "cpu32"})
                if not load_resp.ok:
                    print(f"Failed to load model {model_name}")
                    return
            print(f"Model {model_name} loaded for camera {camera_id}")
            # 2. Poll for inference results
            active_event = None
            while thread_key not in thread_control or not thread_control[thread_key]:
                inf_resp = requests.post(f"{AI_INFERENCE_URL}/inference/latest-frame", params={"camera_id": camera_id, "model_name": model_name, "accelerator": "cpu32"})
                if inf_resp.ok:
                    result = inf_resp.json()
                    detections = result.get("detections", [])
                    ai_annotation_path = result.get("ai_annotation_path")
                    timestamp = result.get("frame_timestamp")
                    # If detection found, create or update event
                    if detections:
                        if not active_event:
                            # Start new event
                            event = AlertEventCreate(
                                camera_id=camera_id,
                                alert_type=alert_type,
                                start_time=datetime.utcnow(),
                                ai_annotation_path=ai_annotation_path,
                                detection_results=detections
                            )
                            db_event = create_alert_event(session, event)
                            active_event = db_event
                        else:
                            # Update detection results and annotation path
                            update = AlertEventUpdate(
                                ai_annotation_path=ai_annotation_path,
                                detection_results=detections
                            )
                            update_alert_event(session, active_event.id, update)
                    else:
                        # No detection: close event if active
                        if active_event:
                            close_alert_event(session, active_event.id, datetime.utcnow())
                            active_event = None
                time.sleep(1)
            print(f"Polling stopped for camera {camera_id}, model {model_name}")
        finally:
            session.close()
            # Clean up thread control
            if thread_key in thread_control:
                del thread_control[thread_key]

    thread_key = (camera_id, model_name)
    if thread_key in alert_polling_threads:
        print(f"Polling already running for camera {camera_id}, model {model_name}")
        return
    # Initialize thread control
    thread_control[thread_key] = False
    thread = threading.Thread(target=polling_loop, daemon=True)
    alert_polling_threads[thread_key] = thread
    thread.start()

@router.get("/", response_model=List[AlertEngine])
def get_all_alert_engines(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all alert engine configurations"""
    return alert_engine_crud.get_all_alert_engines(db, skip=skip, limit=limit)

@router.post("/", response_model=AlertEngine, status_code=status.HTTP_201_CREATED)
def create_alert_engine(
    alert_engine: AlertEngineCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert engine configuration"""
    # Check if alert engine name already exists
    if alert_engine_crud.get_alert_engine_by_name(db, alert_engine.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert engine with this name already exists"
        )
    # For human_detection, set is_active to False by default
    is_human_detection = alert_engine.type == "human_detection"
    engine_data = alert_engine.model_dump()
    if is_human_detection:
        engine_data["is_active"] = False
    db_alert_engine = alert_engine_crud.create_alert_engine(db, AlertEngineCreate(**engine_data))
    return db_alert_engine

@router.get("/{alert_engine_id}", response_model=AlertEngine)
def get_alert_engine(
    alert_engine_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific alert engine configuration"""
    db_alert_engine = alert_engine_crud.get_alert_engine(db, alert_engine_id)
    if not db_alert_engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert engine not found"
        )
    return db_alert_engine

@router.put("/{alert_engine_id}", response_model=AlertEngine)
def update_alert_engine(
    alert_engine_id: int,
    alert_engine: AlertEngineUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert engine configuration"""
    db_alert_engine = alert_engine_crud.update_alert_engine(db, alert_engine_id, alert_engine)
    if not db_alert_engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert engine not found"
        )
    return db_alert_engine

@router.delete("/{alert_engine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_engine(
    alert_engine_id: int,
    db: Session = Depends(get_db)
):
    """Delete an alert engine configuration"""
    success = alert_engine_crud.delete_alert_engine(db, alert_engine_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert engine not found"
        )

@router.get("/camera/{camera_id}", response_model=List[AlertEngine])
def get_camera_alert_engines(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """Get all alert engine configurations for a specific camera"""
    return alert_engine_crud.get_camera_alert_engines(db, camera_id)

@router.post("/camera", status_code=status.HTTP_201_CREATED)
def add_alert_engine_to_camera(
    camera_alert_engine: CameraAlertEngineCreate,
    db: Session = Depends(get_db)
):
    """Add an alert engine configuration to a camera"""
    success = alert_engine_crud.add_alert_engine_to_camera(
        db, 
        camera_alert_engine.camera_id, 
        camera_alert_engine.alert_engine_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera or alert engine configuration not found"
        )
    # If this is a human_detection engine, start polling and set active
    engine = alert_engine_crud.get_alert_engine(db, camera_alert_engine.alert_engine_id)
    if engine and engine.type == "human_detection":
        from app.database import SessionLocal
        try:
            start_alert_polling(camera_alert_engine.camera_id, "person", "human_detection", SessionLocal)
            alert_engine_crud.update_alert_engine(db, engine.id, AlertEngineUpdate(is_active=True))
        except Exception as e:
            print(f"Failed to start polling for camera {camera_alert_engine.camera_id}: {e}")
    return {"message": "Alert engine added to camera successfully"}

@router.delete("/camera/{camera_id}/{alert_engine_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_alert_engine_from_camera(
    camera_id: int,
    alert_engine_id: int,
    db: Session = Depends(get_db)
):
    """Remove an alert engine configuration from a camera"""
    success = alert_engine_crud.remove_alert_engine_from_camera(db, camera_id, alert_engine_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera or alert engine configuration not found"
        )

@router.patch("/{alert_engine_id}/toggle", response_model=AlertEngine)
def toggle_alert_engine_active(
    alert_engine_id: int,
    db: Session = Depends(get_db)
):
    """Toggle alert engine active status"""
    db_alert_engine = alert_engine_crud.toggle_alert_engine_active(db, alert_engine_id)
    if not db_alert_engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert engine not found"
        )
    
    # If this is a human_detection engine and it's now inactive, stop polling
    if db_alert_engine.type == "human_detection" and not db_alert_engine.is_active:
        # Find cameras using this alert engine and stop polling
        camera_engines = alert_engine_crud.get_cameras_by_alert_engine(db, alert_engine_id)
        for camera_engine in camera_engines:
            stop_alert_polling(camera_engine.id, "person")
    
    return db_alert_engine

@router.get("/{alert_engine_id}/snapshot", response_class=FileResponse)
def get_latest_snapshot(
    alert_engine_id: int,
    db: Session = Depends(get_db)
):
    """Get the latest AI annotated snapshot for an alert engine"""
    db_alert_engine = alert_engine_crud.get_alert_engine(db, alert_engine_id)
    if not db_alert_engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert engine not found"
        )
    snapshot_path = db_alert_engine.ai_annotation_path
    if not snapshot_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI annotation path found for this alert engine"
        )
    return FileResponse(snapshot_path)

@router.get("/{alert_engine_id}/latest-annotated-snapshot")
def get_latest_annotated_snapshot(
    alert_engine_id: int,
    db: Session = Depends(get_db)
):
    """Get the latest AI annotated snapshot for an alert engine"""
    # Get the alert engine
    db_alert_engine = alert_engine_crud.get_alert_engine(db, alert_engine_id)
    if not db_alert_engine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert engine not found"
        )
    
    # Get cameras using this alert engine
    cameras = alert_engine_crud.get_cameras_by_alert_engine(db, alert_engine_id)
    if not cameras:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cameras assigned to this alert engine"
        )
    
    # For now, use the first camera (we could enhance this to show multiple)
    camera = cameras[0]
    
    try:
        # Get the latest annotated frame from AI inference
        model_name = "person"  # Default for human detection
        if db_alert_engine.type == "human_detection":
            model_name = "person"
        
        print(f"Requesting latest frame for camera {camera.id}, model {model_name}")
        inf_resp = requests.post(f"{AI_INFERENCE_URL}/inference/latest-frame", 
                               params={"camera_id": camera.id, "model_name": model_name, "accelerator": "cpu32"})
        
        print(f"AI inference response status: {inf_resp.status_code}")
        
        if inf_resp.ok:
            result = inf_resp.json()
            ai_annotation_path = result.get("ai_annotation_path")
            frame_path = result.get("frame_path")
            
            print(f"AI annotation path: {ai_annotation_path}")
            print(f"Frame path: {frame_path}")
            
            # Convert paths to shared volume paths
            if ai_annotation_path:
                # Convert /app/frames/... to /app/shared/frames/...
                shared_ai_path = ai_annotation_path.replace("/app/frames/", "/app/shared/frames/")
                if os.path.exists(shared_ai_path):
                    return FileResponse(shared_ai_path, media_type="image/jpeg")
            
            if frame_path:
                # Convert /app/frames/... to /app/shared/frames/...
                shared_frame_path = frame_path.replace("/app/frames/", "/app/shared/frames/")
                if os.path.exists(shared_frame_path):
                    return FileResponse(shared_frame_path, media_type="image/jpeg")
            
            print(f"Paths don't exist in shared volume - ai_annotation_path: {ai_annotation_path}, frame_path: {frame_path}")
        
        print(f"AI inference request failed with status {inf_resp.status_code}: {inf_resp.text}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No snapshot available"
        )
        
    except Exception as e:
        print(f"Error getting annotated snapshot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get annotated snapshot"
        ) 