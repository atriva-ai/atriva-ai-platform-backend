from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import httpx
import os
import logging
import json
from ..database import get_db
from ..db.models.camera import Camera as CameraModel
from ..db.schemas.camera import CameraCreate, CameraUpdate, CameraInDB
from ..db.crud import camera as camera_crud
from io import BytesIO

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/cameras",
    tags=["cameras"]
)

# Service configurations
VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "http://video-pipeline:8002")
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://ai_inference:8001")

# Runtime status manager - simple in-memory storage
camera_status: Dict[int, Dict] = {}

# Startup initialization flag
_startup_initialized = False

async def get_video_pipeline_client():
    """Get HTTP client for video pipeline service"""
    async with httpx.AsyncClient() as client:
        yield client

def get_camera_status(camera_id: int) -> Dict:
    """Get camera runtime status"""
    if camera_id not in camera_status:
        camera_status[camera_id] = {
            "is_active": False,
            "streaming_status": "stopped"
        }
    return camera_status[camera_id]

def update_camera_status(camera_id: int, is_active: bool = None, streaming_status: str = None):
    """Update camera runtime status"""
    if camera_id not in camera_status:
        camera_status[camera_id] = {
            "is_active": False,
            "streaming_status": "stopped"
        }
    
    if is_active is not None:
        camera_status[camera_id]["is_active"] = is_active
    if streaming_status is not None:
        camera_status[camera_id]["streaming_status"] = streaming_status

async def initialize_cameras_on_startup(db: Session, client: httpx.AsyncClient):
    """Initialize cameras on startup - re-activate active cameras and start tracking"""
    global _startup_initialized
    if _startup_initialized:
        return
    
    print("🚀 STARTUP INITIALIZATION: Initializing cameras on startup...")
    try:
        # Get all cameras from database
        cameras = camera_crud.get_cameras(db, skip=0, limit=1000)
        print(f"🚀 STARTUP: Found {len(cameras)} cameras in database")
        
        for camera in cameras:
            print(f"🚀 STARTUP: Checking camera {camera.id}: is_active={camera.is_active}, vehicle_tracking_enabled={camera.vehicle_tracking_enabled}")
            print(f"🚀 STARTUP: Camera {camera.id} vehicle_tracking_enabled type: {type(camera.vehicle_tracking_enabled)}")
            
            # Initialize runtime status
            update_camera_status(camera.id, is_active=camera.is_active, streaming_status="stopped")
            
            # Stop inactive cameras that might be running
            if not camera.is_active and camera.rtsp_url:
                try:
                    print(f"🛑 STARTUP: Stopping inactive camera {camera.id} on startup (is_active={camera.is_active})")
                    stop_response = await client.post(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/stop/", 
                                                    json={"camera_id": str(camera.id)})
                    if stop_response.status_code == 200:
                        print(f"✅ Stopped inactive camera {camera.id}")
                    else:
                        print(f"⚠️ Failed to stop inactive camera {camera.id}: {stop_response.status_code}")
                except Exception as e:
                    print(f"⚠️ Error stopping inactive camera {camera.id}: {e}")
            
            # Re-activate camera if it's active and has RTSP URL
            elif camera.is_active and camera.rtsp_url:
                try:
                    print(f"🔄 STARTUP: Re-activating camera {camera.id} (is_active={camera.is_active})")
                    decode_data = {
                        "camera_id": str(camera.id),
                        "url": camera.rtsp_url,
                        "fps": 1,
                        "force_format": "rkmpp"
                    }
                    decode_response = await client.post(
                        f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
                        data=decode_data,
                        timeout=30.0
                    )
                    if decode_response.status_code == 200:
                        print(f"✅ Camera {camera.id} re-activated successfully")
                        update_camera_status(camera.id, streaming_status="streaming")
                    else:
                        print(f"❌ Failed to re-activate camera {camera.id}: {decode_response.status_code}")
                except Exception as e:
                    print(f"❌ Error re-activating camera {camera.id}: {str(e)}")
            
            # Re-start vehicle tracking if enabled
            if camera.vehicle_tracking_enabled:
                try:
                    print(f"🔄 Re-starting vehicle tracking for camera {camera.id} using inference endpoint")
                    ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_inference:8001")
                    tracking_response = await client.post(
                        f"{ai_service_url}/vehicle-tracking/start/",
                        json={"camera_id": str(camera.id)},
                        timeout=10.0
                    )
                    if tracking_response.status_code == 200:
                        print(f"✅ Vehicle tracking re-started for camera {camera.id}")
                    else:
                        print(f"❌ Failed to re-start vehicle tracking for camera {camera.id}: {tracking_response.status_code}")
                except Exception as e:
                    print(f"❌ Error re-starting vehicle tracking for camera {camera.id}: {str(e)}")
        
        _startup_initialized = True
        print("✅ Camera startup initialization completed")
        
    except Exception as e:
        print(f"❌ Error during camera startup initialization: {str(e)}")

@router.get("/", response_model=List[CameraInDB])
def list_cameras(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    List all cameras
    """
    return camera_crud.get_cameras(db, skip=skip, limit=limit)

@router.post("/", response_model=dict)
async def create_camera(
    camera: CameraCreate,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    print(f"[DEBUG] create_camera called with: {camera}")
    """
    Create a new camera and validate the video stream (get video info only)
    """
    # First, create the camera in the database with the provided active status
    camera_data = camera.model_dump()
    print(f"🔍 DEBUG: Original camera data: {camera_data}")
    # Use the provided is_active value - don't override it!
    if 'is_active' not in camera_data:
        camera_data['is_active'] = False  # Default to inactive for new cameras
        print(f"🔍 DEBUG: Set default is_active=False")
    else:
        print(f"🔍 DEBUG: Using provided is_active={camera_data['is_active']}")
    print(f"🔍 DEBUG: Final camera_data: {camera_data}")
    db_camera = camera_crud.create_camera(db=db, camera=CameraCreate(**camera_data))
    
    # CRITICAL: Check what was actually saved to the database
    print(f"🔍 DATABASE CHECK: db_camera.is_active = {db_camera.is_active}")
    print(f"🔍 DATABASE CHECK: db_camera.id = {db_camera.id}")
    print(f"🔍 DATABASE CHECK: db_camera.name = {db_camera.name}")
    
    # Initialize runtime status using ACTUAL database value
    update_camera_status(db_camera.id, is_active=db_camera.is_active, streaming_status="stopped")
    
    # Convert SQLAlchemy model to Pydantic schema for serialization
    camera_schema = CameraInDB.model_validate(db_camera)
    
    # Initialize response with camera data
    response = {
        "camera": camera_schema,
        "video_validation": {
            "status": "pending",
            "video_info": None,
            "errors": []
        }
    }
    
    # If camera is active and has RTSP URL, start decoding automatically
    # Use the ACTUAL database value, not the request data
    if db_camera.is_active and camera.rtsp_url:
        try:
            print(f"🚀 Auto-starting camera {db_camera.id} (is_active=True)")
            decode_data = {
                "camera_id": str(db_camera.id),
                "url": camera.rtsp_url,
                "fps": 1,
                "force_format": "rkmpp"  # Use rkmpp hardware acceleration by default
            }
            decode_response = await client.post(
                f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
                data=decode_data,
                timeout=30.0
            )
            if decode_response.status_code == 200:
                print(f"✅ Auto-started camera {db_camera.id}")
                response["video_validation"]["auto_started"] = True
            else:
                print(f"❌ Failed to auto-start camera {db_camera.id}: {decode_response.status_code}")
                response["video_validation"]["errors"].append(f"Failed to auto-start camera: {decode_response.status_code}")
        except Exception as e:
            print(f"❌ Error auto-starting camera {db_camera.id}: {str(e)}")
            response["video_validation"]["errors"].append(f"Auto-start error: {str(e)}")
    else:
        print(f"⏸️ Camera {db_camera.id} created but not auto-started (is_active={db_camera.is_active}, has_rtsp={bool(camera.rtsp_url)})")
    
    # Start vehicle tracking if enabled (use database value)
    print(f"🔍 VEHICLE TRACKING CHECK: db_camera.vehicle_tracking_enabled = {db_camera.vehicle_tracking_enabled}")
    print(f"🔍 VEHICLE TRACKING CHECK: type = {type(db_camera.vehicle_tracking_enabled)}")
    if db_camera.vehicle_tracking_enabled:
        try:
            print(f"🚗 Starting vehicle tracking for camera {db_camera.id}")
            ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_inference:8001")
            tracking_response = await client.post(
                f"{ai_service_url}/vehicle-tracking/start/",
                json={"camera_id": str(db_camera.id)},
                timeout=10.0
            )
            if tracking_response.status_code == 200:
                print(f"✅ Vehicle tracking started for camera {db_camera.id}")
                response["video_validation"]["vehicle_tracking_started"] = True
            else:
                print(f"❌ Failed to start vehicle tracking for camera {db_camera.id}: {tracking_response.status_code}")
                response["video_validation"]["errors"].append(f"Failed to start vehicle tracking: {tracking_response.status_code}")
        except Exception as e:
            print(f"❌ Error starting vehicle tracking for camera {db_camera.id}: {str(e)}")
            response["video_validation"]["errors"].append(f"Vehicle tracking start error: {str(e)}")
    else:
        print(f"⏸️ Vehicle tracking NOT started for camera {db_camera.id} (vehicle_tracking_enabled=False)")
    
    # Get video information if RTSP URL is provided
    if camera.rtsp_url:
        try:
            print(f"🔍 Getting video info for camera {db_camera.id}: {camera.rtsp_url}")
            
            # Get video information only (no decoding)
            try:
                video_info_data = {"url": camera.rtsp_url}
                print(f"Video info data: {video_info_data}")
                video_info_response = await client.post(
                    f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/video-info-url/",
                    data=video_info_data,
                    timeout=30.0
                )
                print(f"Video info response: {video_info_response}")
                if video_info_response.status_code == 200:
                    video_info = video_info_response.json()
                    response["video_validation"]["video_info"] = video_info
                    response["video_validation"]["status"] = "validated"
                    
                    # Save video info to database
                    camera_crud.update_camera(
                        db=db, 
                        camera_id=db_camera.id, 
                        camera_update=CameraUpdate(video_info=video_info)
                    )
                    
                    print(f"✅ Video info retrieved and saved for camera {db_camera.id}")
                else:
                    response["video_validation"]["errors"].append(f"Failed to get video info: {video_info_response.status_code}")
                    print(f"❌ Failed to get video info for camera {db_camera.id}")
                    
            except httpx.TimeoutException:
                response["video_validation"]["errors"].append("Video info request timed out")
                print(f"⏰ Video info request timed out for camera {db_camera.id}")
            except Exception as e:
                response["video_validation"]["errors"].append(f"Video info error: {str(e)}")
                print(f"❌ Video info error for camera {db_camera.id}: {str(e)}")
                
        except Exception as e:
            response["video_validation"]["errors"].append(f"Video validation failed: {str(e)}")
            print(f"❌ Video validation failed for camera {db_camera.id}: {str(e)}")
    
    return response

@router.get("/{camera_id}/", response_model=CameraInDB)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific camera by ID
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return CameraInDB.model_validate(db_camera)

@router.put("/{camera_id}/", response_model=CameraInDB)
async def update_camera(
    camera_id: int,
    camera_update: CameraUpdate,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Update a camera
    """
    print(f"🔄 UPDATE CAMERA API CALL - Camera ID: {camera_id}")
    print(f"🔄 Request data: {camera_update}")
    print(f"🔄 Request model dump: {camera_update.model_dump(exclude_unset=True)}")
    
    # Get current camera state BEFORE update
    current_camera = camera_crud.get_camera(db, camera_id=camera_id)
    print(f"📷 Current camera data: {current_camera}")
    print(f"📷 Current camera is_active: {current_camera.is_active if current_camera else 'None'}")
    print(f"📷 Current camera type: {type(current_camera.is_active) if current_camera else 'None'}")
    if current_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Handle enable/disable logic BEFORE updating the database
    update_data = camera_update.model_dump(exclude_unset=True)
    print(f"🔍 Update data keys: {list(update_data.keys())}")
    print(f"🔍 Full update data: {update_data}")
    
    # If is_active status changed, handle enable/disable
    if 'is_active' in update_data:
        print(f"🎯 is_active field detected in update!")
        new_active_status = update_data['is_active']
        old_active_status = current_camera.is_active  # Read OLD status BEFORE update
        
        print(f"🔍 Status comparison for camera {camera_id}:")
        print(f"   - Old status: {old_active_status} (type: {type(old_active_status)})")
        print(f"   - New status: {new_active_status} (type: {type(new_active_status)})")
        print(f"   - Status changed: {new_active_status != old_active_status}")
        print(f"   - Raw comparison: {new_active_status} != {old_active_status} = {new_active_status != old_active_status}")
        
        if new_active_status != old_active_status:
            print(f"🔄 Camera {camera_id} active status changed: {old_active_status} -> {new_active_status}")
            
            if new_active_status:
                # Enable camera - start decoding if RTSP URL exists
                if current_camera.rtsp_url:
                    try:
                        print(f"🚀 ACTIVATE CAMERA {camera_id} - Starting video pipeline decode")
                        print(f"🚀 VIDEO PIPELINE URL: {VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/")
                        decode_data = {
                            "camera_id": str(camera_id),
                            "url": current_camera.rtsp_url,
                            "fps": 1,
                            "force_format": "rkmpp"
                        }
                        print(f"🚀 DECODE REQUEST DATA: {decode_data}")
                        print(f"🚀 Making HTTP POST request to video pipeline...")
                        
                        decode_response = await client.post(
                            f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
                            data=decode_data,
                            timeout=30.0
                        )
                        
                        print(f"🚀 VIDEO PIPELINE RESPONSE STATUS: {decode_response.status_code}")
                        print(f"🚀 VIDEO PIPELINE RESPONSE TEXT: {decode_response.text}")
                        
                        if decode_response.status_code == 200:
                            print(f"✅ SUCCESS: Camera {camera_id} decode started successfully")
                        else:
                            print(f"❌ FAILED: Start decode for camera {camera_id}: {decode_response.status_code}")
                            print(f"❌ FAILED RESPONSE: {decode_response.text}")
                    except Exception as e:
                        print(f"❌ EXCEPTION: Error starting decode for camera {camera_id}: {e}")
                        print(f"❌ EXCEPTION TYPE: {type(e)}")
                else:
                    print(f"⚠️ Camera {camera_id} enabled but no RTSP URL provided")
            else:
                # Disable camera - stop decoding
                try:
                    print(f"🛑 DEACTIVATE CAMERA {camera_id} - Stopping video pipeline decode")
                    print(f"🛑 VIDEO PIPELINE URL: {VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/stop/")
                    stop_data = {"camera_id": str(camera_id)}
                    print(f"🛑 STOP REQUEST DATA: {stop_data}")
                    print(f"🛑 Making HTTP POST request to video pipeline...")
                    
                    stop_response = await client.post(
                        f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/stop/",
                        data=stop_data,
                        timeout=10.0
                    )
                    
                    print(f"🛑 VIDEO PIPELINE RESPONSE STATUS: {stop_response.status_code}")
                    print(f"🛑 VIDEO PIPELINE RESPONSE TEXT: {stop_response.text}")
                    
                    if stop_response.status_code == 200:
                        print(f"✅ SUCCESS: Camera {camera_id} decode stopped successfully")
                    else:
                        print(f"❌ FAILED: Stop decode for camera {camera_id}: {stop_response.status_code}")
                        print(f"❌ FAILED RESPONSE: {stop_response.text}")
                except Exception as e:
                    print(f"❌ EXCEPTION: Error stopping decode for camera {camera_id}: {e}")
                    print(f"❌ EXCEPTION TYPE: {type(e)}")
            
            # Update runtime status
            update_camera_status(camera_id, is_active=new_active_status)
    
    # Handle vehicle tracking enable/disable BEFORE updating the database
    print(f"🔍 Update data for camera {camera_id}: {update_data}")
    print(f"🔍 vehicle_tracking_enabled in update_data: {'vehicle_tracking_enabled' in update_data}")
    
    if 'vehicle_tracking_enabled' in update_data:
        new_tracking_status = update_data['vehicle_tracking_enabled']
        old_tracking_status = current_camera.vehicle_tracking_enabled  # Read OLD status BEFORE update
        
        print(f"🔍 Vehicle tracking update check for camera {camera_id}:")
        print(f"   - Old status: {old_tracking_status}")
        print(f"   - New status: {new_tracking_status}")
        print(f"   - Status changed: {new_tracking_status != old_tracking_status}")
        
        if new_tracking_status != old_tracking_status:
            print(f"🔄 Camera {camera_id} vehicle tracking status changed: {old_tracking_status} -> {new_tracking_status}")
            
            try:
                # Call AI service to start/stop vehicle tracking
                ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_inference:8001")
                
                if new_tracking_status:
                    # Start vehicle tracking - use existing inference endpoint
                    print(f"🚗 Starting vehicle tracking for camera {camera_id} using inference endpoint")
                    tracking_response = await client.post(
                        f"{ai_service_url}/vehicle-tracking/start/",
                        json={"camera_id": str(camera_id)},
                        timeout=10.0
                    )
                    if tracking_response.status_code == 200:
                        print(f"✅ Vehicle tracking started for camera {camera_id}")
                    else:
                        print(f"❌ Failed to start vehicle tracking for camera {camera_id}: {tracking_response.status_code}")
                else:
                    # Stop vehicle tracking
                    tracking_response = await client.post(
                        f"{ai_service_url}/vehicle-tracking/stop/",
                        json={"camera_id": str(camera_id)},
                        timeout=10.0
                    )
                    if tracking_response.status_code == 200:
                        print(f"✅ Vehicle tracking stopped for camera {camera_id}")
                    else:
                        print(f"❌ Failed to stop vehicle tracking for camera {camera_id}: {tracking_response.status_code}")
            except Exception as e:
                print(f"❌ Error managing vehicle tracking for camera {camera_id}: {str(e)}")
    
    # NOW update the camera in the database
    db_camera = camera_crud.update_camera(db, camera_id=camera_id, camera_update=camera_update)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return CameraInDB.model_validate(db_camera)

@router.delete("/{camera_id}/")
async def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Delete a camera
    """
    # First stop video decoding if it's running
    try:
        print(f"🛑 Stopping video decode for camera {camera_id} before deletion")
        stop_response = await client.post(
            f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/stop/",
            data={"camera_id": str(camera_id)},
            timeout=10.0
        )
        if stop_response.status_code == 200:
            print(f"✅ Video decode stopped for camera {camera_id}")
        else:
            print(f"⚠️ Failed to stop video decode for camera {camera_id}: {stop_response.status_code}")
    except Exception as e:
        print(f"⚠️ Error stopping video decode for camera {camera_id}: {str(e)}")
    
    # Stop vehicle tracking if it's running
    try:
        print(f"🛑 Stopping vehicle tracking for camera {camera_id} before deletion")
        ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_inference:8001")
        tracking_response = await client.post(
            f"{ai_service_url}/vehicle-tracking/stop/",
            json={"camera_id": str(camera_id)},
            timeout=10.0
        )
        if tracking_response.status_code == 200:
            print(f"✅ Vehicle tracking stopped for camera {camera_id}")
        else:
            print(f"⚠️ Failed to stop vehicle tracking for camera {camera_id}: {tracking_response.status_code}")
    except Exception as e:
        print(f"⚠️ Error stopping vehicle tracking for camera {camera_id}: {str(e)}")
    
    # Now delete the camera from database
    success = camera_crud.delete_camera(db, camera_id=camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Clean up runtime status
    if camera_id in camera_status:
        del camera_status[camera_id]
        print(f"✅ Runtime status cleaned up for camera {camera_id}")
    
    return {"message": "Camera deleted successfully"}

@router.post("/{camera_id}/validate-video/")
async def validate_camera_video(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Manually validate video stream for an existing camera
    """
    # Get the camera from database
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Initialize response
    response = {
        "camera_id": camera_id,
        "rtsp_url": db_camera.rtsp_url,
        "validation": {
            "status": "pending",
            "video_info": None,
            "decode_status": None,
            "errors": []
        }
    }
    
    # Validate the video stream if RTSP URL is provided
    if db_camera.rtsp_url:
        try:
            print(f"🔍 Validating video stream for camera {camera_id}: {db_camera.rtsp_url}")
            
            # Step 1: Get video information
            try:
                video_info_response = await client.post(
                    f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/video-info-url/",
                    data={"url": db_camera.rtsp_url},
                    timeout=30.0
                )
                
                if video_info_response.status_code == 200:
                    video_info_result = video_info_response.json()
                    if video_info_result.get("info", {}).get("codec"):
                        # Video info acquired successfully - set is_active to true
                        update_camera_status(camera_id, is_active=True, streaming_status="stopped")
                        response["validation"]["video_info"] = video_info_result["info"]
                        response["validation"]["status"] = "video_info_acquired"
                        print(f"✅ Video info acquired for camera {camera_id}")
                    else:
                        response["validation"]["errors"].append("Invalid video stream - no codec found")
                        print(f"❌ Invalid video stream for camera {camera_id}")
                else:
                    response["validation"]["errors"].append(f"Failed to get video info: {video_info_response.status_code}")
                    print(f"❌ Failed to get video info for camera {camera_id}")
                    
            except httpx.TimeoutException:
                response["validation"]["errors"].append("Video info request timed out")
                print(f"⏰ Video info request timed out for camera {camera_id}")
            except Exception as e:
                response["validation"]["errors"].append(f"Video info error: {str(e)}")
                print(f"❌ Video info error for camera {camera_id}: {str(e)}")
            
            # Step 2: Start video decoding (extract frames)
            try:
                decode_data = {
                    "camera_id": str(camera_id),
                    "url": db_camera.rtsp_url,
                    "fps": 1,  # Extract 1 frame per second for validation
                    "force_format": "rkmpp"  # Use rkmpp hardware acceleration for validation
                }
                print(f"[DEBUG] Sending decode request to video pipeline for camera_id={camera_id}, url={db_camera.rtsp_url}, payload={decode_data}")
                decode_response = await client.post(
                    f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
                    data=decode_data,
                    timeout=60.0  # Longer timeout for decoding
                )
                print(f"[DEBUG] Video pipeline decode response for camera_id={camera_id}: status={decode_response.status_code}, body={decode_response.text}")
                
                if decode_response.status_code == 200:
                    decode_result = decode_response.json()
                    response["validation"]["decode_status"] = decode_result
                    response["validation"]["status"] = "decoding_started"
                    print(f"✅ Video decoding started for camera {camera_id}")
                else:
                    response["validation"]["errors"].append(f"Failed to start decoding: {decode_response.status_code}")
                    print(f"❌ Failed to start decoding for camera {camera_id}")
                    
            except httpx.TimeoutException:
                response["validation"]["errors"].append("Decode request timed out")
                print(f"⏰ Decode request timed out for camera {camera_id}")
            except Exception as e:
                response["validation"]["errors"].append(f"Decode error: {str(e)}")
                print(f"❌ Decode error for camera {camera_id}: {str(e)}")
                
        except Exception as e:
            response["validation"]["errors"].append(f"Video validation failed: {str(e)}")
            print(f"❌ Video validation failed for camera {camera_id}: {str(e)}")
    else:
        response["validation"]["errors"].append("No RTSP URL provided for camera")
    
    return response

@router.post("/{camera_id}/activate/")
async def activate_camera(
    camera_id: int,
    fps: Optional[int] = 1,
    force_format: Optional[str] = "rkmpp",
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    print(f"[DEBUG] activate_camera called for camera_id={camera_id}, fps={fps}, force_format={force_format}")
    """
    Activate a camera by starting video decoding
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    if not db_camera.rtsp_url:
        raise HTTPException(status_code=400, detail="Camera has no RTSP URL")

    response = {
        "camera_id": camera_id,
        "rtsp_url": db_camera.rtsp_url,
        "activation": {
            "status": "pending",
            "decode_status": None,
            "errors": []
        }
    }
    try:
        print(f"🚀 Activating camera {camera_id}: {db_camera.rtsp_url}")
        decode_data = {
            "camera_id": str(camera_id),
            "url": db_camera.rtsp_url,
            "fps": fps,
            "force_format": force_format or "none"
        }
        decode_response = await client.post(
            f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
            data=decode_data,
            timeout=60.0
        )
        
        if decode_response.status_code == 200:
            decode_result = decode_response.json()
            response["activation"]["decode_status"] = decode_result
            
            # Check if decode was already running
            if decode_result.get("status") == "already_running":
                response["activation"]["status"] = "already_running"
                print(f"✅ Camera {camera_id} was already running")
                return response
            
            # Check decode status after a short delay to see if it started successfully
            import asyncio
            await asyncio.sleep(3)  # Increased delay to allow more time for startup
            
            status_response = await client.get(
                f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/status/",
                params={"camera_id": str(camera_id)},
                timeout=10.0
            )
            if status_response.status_code == 200:
                status_result = status_response.json()
                if status_result.get("status") == "running" and status_result.get("frame_count", 0) > 0:
                    response["activation"]["status"] = "activated"
                    # Set streaming status to streaming when successful
                    update_camera_status(camera_id, streaming_status="streaming")
                    print(f"✅ Camera {camera_id} activated successfully")
                else:
                    response["activation"]["status"] = "error"
                    last_error = status_result.get("last_error", "Unknown error")
                    response["activation"]["errors"].append(f"Decode failed: {last_error}")
                    print(f"❌ Decode failed for camera {camera_id}: {last_error}")
            else:
                response["activation"]["status"] = "error"
                response["activation"]["errors"].append(f"Failed to get decode status: {status_response.status_code}")
        else:
            # Get detailed error from response
            try:
                error_detail = decode_response.json()
                error_msg = error_detail.get("detail", f"HTTP {decode_response.status_code}")
            except:
                error_msg = f"HTTP {decode_response.status_code}"
            
            response["activation"]["status"] = "error"
            response["activation"]["errors"].append(f"Failed to start decoding: {error_msg}")
            print(f"❌ Failed to activate camera {camera_id}: {error_msg}")
    except httpx.TimeoutException:
        response["activation"]["status"] = "error"
        response["activation"]["errors"].append("Activation request timed out - check if RTSP stream is accessible")
        print(f"⏰ Activation request timed out for camera {camera_id}")
    except Exception as e:
        response["activation"]["status"] = "error"
        response["activation"]["errors"].append(f"Activation error: {str(e)}")
        print(f"❌ Activation error for camera {camera_id}: {str(e)}")
    return response

@router.post("/{camera_id}/deactivate/")
async def deactivate_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Deactivate a camera by stopping video decoding
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        stop_response = await client.post(
            f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/stop/",
            data={"camera_id": str(camera_id)},
            timeout=10.0
        )
        if stop_response.status_code == 200:
            # Set streaming status to stopped when successful
            update_camera_status(camera_id, streaming_status="stopped")
            return {"message": "Camera deactivated", "camera_id": camera_id}
        else:
            raise HTTPException(status_code=500, detail=f"Failed to stop decoding: {stop_response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate camera: {str(e)}")

@router.get("/{camera_id}/decode-status/")
async def get_decode_status(
    camera_id: int,
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Get the decode status for a camera
    """
    try:
        # Get current runtime status
        runtime_status = get_camera_status(camera_id)
        
        # Get video pipeline status
        status_response = await client.get(
            f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/status/",
            params={"camera_id": str(camera_id)},
            timeout=10.0
        )
        
        if status_response.status_code == 200:
            pipeline_status = status_response.json()
            pipeline_status_value = pipeline_status.get("status", "not_started")
            frame_count = pipeline_status.get("frame_count", 0)
            
            # Update runtime status based on stable pipeline state
            if pipeline_status_value == "running" and frame_count > 0:
                # Decoder is running and producing frames - set to streaming
                update_camera_status(camera_id, streaming_status="streaming")
                runtime_status["streaming_status"] = "streaming"
            elif pipeline_status_value == "stopped" or pipeline_status_value == "not_started":
                # Decoder is stopped - set to stopped
                update_camera_status(camera_id, streaming_status="stopped")
                runtime_status["streaming_status"] = "stopped"
            elif pipeline_status_value == "error":
                # Decoder has error - set to error
                update_camera_status(camera_id, streaming_status="error")
                runtime_status["streaming_status"] = "error"
            
            # Return combined status
            return {
                "camera_id": str(camera_id),
                "status": pipeline_status_value,
                "streaming_status": runtime_status["streaming_status"],
                "is_active": runtime_status["is_active"],
                "frame_count": frame_count,
                "last_error": pipeline_status.get("last_error")
            }
        else:
            # If we can't get pipeline status, return current runtime status
            return {
                "camera_id": str(camera_id),
                "status": "unknown",
                "streaming_status": runtime_status["streaming_status"],
                "is_active": runtime_status["is_active"],
                "frame_count": 0,
                "last_error": f"Failed to get decode status: {status_response.status_code}"
            }
    except Exception as e:
        # On any error, return current runtime status
        runtime_status = get_camera_status(camera_id)
        return {
            "camera_id": str(camera_id),
            "status": "error",
            "streaming_status": "error",
            "is_active": runtime_status["is_active"],
            "frame_count": 0,
            "last_error": str(e)
        }

@router.get("/{camera_id}/latest-frame/")
async def get_latest_frame(
    camera_id: int,
    use_tracking: bool = Query(False, description="Use vehicle tracking if enabled"),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client),
    db: Session = Depends(get_db)
):
    """
    Get the latest decoded frame for a camera
    If vehicle tracking is enabled and use_tracking=True, return annotated frame
    """
    try:
        # Check if vehicle tracking is enabled and requested
        db_camera = camera_crud.get_camera(db, camera_id=camera_id)
        should_use_tracking = use_tracking and db_camera and db_camera.vehicle_tracking_enabled
        
        response = await client.get(
            f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/latest-frame/",
            params={"camera_id": str(camera_id)},
            timeout=10.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Video pipeline error: {response.status_code}")
        
        # If vehicle tracking is enabled and requested, get annotated frame from AI service
        if should_use_tracking:
            try:
                # Process frame with vehicle tracking in AI service
                tracking_response = await client.post(
                    f"{AI_SERVICE_URL}/vehicle-tracking/process-frame/",
                    data={"camera_id": str(camera_id), "frame_number": 0},
                    timeout=30.0
                )
                
                if tracking_response.status_code == 200:
                    result = tracking_response.json()
                    ai_annotation_path = result.get("ai_annotation_path")
                    frame_path = result.get("frame_path")
                    
                    # If we have an annotated frame path, try to read it
                    if ai_annotation_path and os.path.exists(ai_annotation_path):
                        with open(ai_annotation_path, 'rb') as f:
                            annotated_frame_bytes = f.read()
                        
                        # Return annotated frame
                        return StreamingResponse(
                            BytesIO(annotated_frame_bytes),
                            media_type="image/jpeg",
                            headers={
                                "Content-Disposition": f"inline; filename=tracked_frame_{camera_id}.jpg",
                                "X-Vehicle-Tracking": "enabled",
                                "X-Tracked-Vehicles": str(result.get("tracked_vehicles", 0)),
                                "X-Saved-Path": ai_annotation_path
                            }
                        )
                    else:
                        # Fallback to original frame if no annotated frame available
                        logger.warning(f"No annotated frame available, returning original frame")
                        
                else:
                    # Fallback to original frame if AI service fails
                    logger.warning(f"AI service failed to process frame, returning original frame")
                    
            except Exception as e:
                logger.error(f"Error processing frame with vehicle tracking: {e}")
                # Fallback to original frame if tracking fails
        
        # Return the original binary content as a streaming response
        return StreamingResponse(
            BytesIO(response.content),
            media_type="image/jpeg",
            headers={"Content-Disposition": f"inline; filename=frame_{camera_id}.jpg"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest frame: {str(e)}")

@router.post("/{camera_id}/vehicle-tracking/start/")
async def start_vehicle_tracking(
    camera_id: int,
    tracking_config: Optional[Dict] = None,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Start vehicle tracking for a camera
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    if not db_camera.vehicle_tracking_enabled:
        raise HTTPException(status_code=400, detail="Vehicle tracking is not enabled for this camera")
    
    try:
        # Proxy request to AI service
        data = {"camera_id": str(camera_id)}
        
        response = await client.post(
            f"{AI_SERVICE_URL}/vehicle-tracking/start/",
            data=data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Update camera configuration if new config provided
            if tracking_config:
                camera_update = CameraUpdate(vehicle_tracking_config=tracking_config)
                camera_crud.update_camera(db, camera_id=camera_id, camera_update=camera_update)
            
            return result
        else:
            raise HTTPException(status_code=response.status_code, detail=f"AI service error: {response.text}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start vehicle tracking: {str(e)}")

@router.post("/{camera_id}/vehicle-tracking/stop/")
async def stop_vehicle_tracking(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Stop vehicle tracking for a camera
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Proxy request to AI service
        response = await client.post(
            f"{AI_SERVICE_URL}/vehicle-tracking/stop/",
            json={"camera_id": str(camera_id)},
            timeout=30.0
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=f"AI service error: {response.text}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop vehicle tracking: {str(e)}")

@router.get("/{camera_id}/vehicle-tracking/status/")
async def get_vehicle_tracking_status(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Get vehicle tracking status for a camera
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Get camera configuration from database
        camera_config = {
            "tracking_enabled": db_camera.vehicle_tracking_enabled,
            "tracking_config": db_camera.vehicle_tracking_config
        }
        
        # Get tracker status from AI service
        response = await client.get(
            f"{AI_SERVICE_URL}/vehicle-tracking/status/{camera_id}",
            timeout=30.0
        )
        
        if response.status_code == 200:
            ai_status = response.json()
            return {
                "camera_id": camera_id,
                **camera_config,
                "tracker_status": ai_status.get("tracker_status", {})
            }
        else:
            # Return camera config even if AI service is unavailable
            return {
                "camera_id": camera_id,
                **camera_config,
                "tracker_status": {"error": "AI service unavailable"}
            }
            
    except Exception as e:
        # Return camera config even if AI service is unavailable
        return {
            "camera_id": camera_id,
            "tracking_enabled": db_camera.vehicle_tracking_enabled,
            "tracking_config": db_camera.vehicle_tracking_config,
            "tracker_status": {"error": f"Failed to get status: {str(e)}"}
        }

@router.put("/{camera_id}/vehicle-tracking/config/")
async def update_vehicle_tracking_config(
    camera_id: int,
    tracking_config: Dict,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Update vehicle tracking configuration for a camera
    """
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Update camera configuration in database
        camera_update = CameraUpdate(vehicle_tracking_config=tracking_config)
        updated_camera = camera_crud.update_camera(db, camera_id=camera_id, camera_update=camera_update)
        
        # Update tracker configuration in AI service
        response = await client.put(
            f"{AI_SERVICE_URL}/vehicle-tracking/config/{camera_id}",
            json=tracking_config,
            timeout=30.0
        )
        
        if response.status_code == 200:
            return {
                "message": "Vehicle tracking configuration updated",
                "camera_id": camera_id,
                "tracking_config": tracking_config
            }
        else:
            # Configuration updated in database but AI service failed
            return {
                "message": "Vehicle tracking configuration updated in database",
                "camera_id": camera_id,
                "tracking_config": tracking_config,
                "warning": "AI service configuration update failed"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update vehicle tracking configuration: {str(e)}")

@router.put("/{camera_id}/vehicle-tracking/enable/")
async def enable_vehicle_tracking(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """
    Enable vehicle tracking for a camera
    """
    print(f"🚗 ENABLE VEHICLE TRACKING API CALL - Camera ID: {camera_id}")
    
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        print(f"❌ ENABLE VEHICLE TRACKING: Camera {camera_id} not found")
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Enable vehicle tracking in database
        print(f"🔄 ENABLE VEHICLE TRACKING: Setting vehicle_tracking_enabled=True for camera {camera_id}")
        camera_update = CameraUpdate(vehicle_tracking_enabled=True)
        updated_camera = camera_crud.update_camera(db, camera_id=camera_id, camera_update=camera_update)
        
        print(f"✅ ENABLE VEHICLE TRACKING: Updated camera {camera_id} vehicle_tracking_enabled = {updated_camera.vehicle_tracking_enabled}")
        
        return {
            "message": "Vehicle tracking enabled",
            "camera_id": camera_id,
            "vehicle_tracking_enabled": True
        }
    except Exception as e:
        print(f"❌ ENABLE VEHICLE TRACKING: Error enabling vehicle tracking for camera {camera_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to enable vehicle tracking: {str(e)}")

@router.put("/{camera_id}/vehicle-tracking/disable/")
async def disable_vehicle_tracking(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """
    Disable vehicle tracking for a camera
    """
    print(f"🚗 DISABLE VEHICLE TRACKING API CALL - Camera ID: {camera_id}")
    
    db_camera = camera_crud.get_camera(db, camera_id=camera_id)
    if db_camera is None:
        print(f"❌ DISABLE VEHICLE TRACKING: Camera {camera_id} not found")
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Stop tracking in AI service if active
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/vehicle-tracking/stop/",
                json={"camera_id": str(camera_id)},
                timeout=30.0
            )
        except Exception:
            # Ignore errors if AI service is unavailable
            pass
        
        # Disable vehicle tracking in database
        print(f"🔄 DISABLE VEHICLE TRACKING: Setting vehicle_tracking_enabled=False for camera {camera_id}")
        camera_update = CameraUpdate(vehicle_tracking_enabled=False)
        updated_camera = camera_crud.update_camera(db, camera_id=camera_id, camera_update=camera_update)
        
        print(f"✅ DISABLE VEHICLE TRACKING: Updated camera {camera_id} vehicle_tracking_enabled = {updated_camera.vehicle_tracking_enabled}")
        
        return {
            "message": "Vehicle tracking disabled",
            "camera_id": camera_id,
            "vehicle_tracking_enabled": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable vehicle tracking: {str(e)}")

# @router.put("/{camera_id}/analytics", response_model=CameraRead)
# def set_camera_analytics(camera_id: int, analytics_config: dict, db: Session = Depends(get_db)):
#     return crud_camera.update_camera_analytics(db, camera_id, analytics_config)
