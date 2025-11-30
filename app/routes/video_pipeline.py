from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.db.crud import camera as camera_crud
from app.db.models.camera import Camera
import httpx
import os

# Create router for video pipeline integration
router = APIRouter(
    prefix="/api/v1/video-pipeline",
    tags=["Video Pipeline"]
)

# Video pipeline service configuration
VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "http://video-pipeline:8002")

async def get_video_pipeline_client():
    """Get HTTP client for video pipeline service"""
    async with httpx.AsyncClient() as client:
        yield client

@router.get("/test-connection/")
async def test_video_pipeline_connection(client: httpx.AsyncClient = Depends(get_video_pipeline_client)):
    """Test connection to video pipeline service"""
    try:
        # Try to connect to the root endpoint first
        response = await client.get(f"{VIDEO_PIPELINE_URL}/")
        root_response = response.json()
        
        # Try to connect to the health endpoint
        health_response = await client.get(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/health/")
        health_data = health_response.json()
        
        # Try to connect to the debug endpoint
        debug_response = await client.get(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/debug/")
        debug_data = debug_response.json()
        
        return {
            "status": "connected",
            "video_pipeline_url": VIDEO_PIPELINE_URL,
            "root_endpoint": root_response,
            "health_endpoint": health_data,
            "debug_endpoint": debug_data
        }
    except httpx.ConnectError as e:
        return {
            "status": "connection_failed",
            "video_pipeline_url": VIDEO_PIPELINE_URL,
            "error": f"Connection error: {str(e)}",
            "suggestion": "Check if video-pipeline service is running and accessible"
        }
    except httpx.TimeoutException as e:
        return {
            "status": "timeout",
            "video_pipeline_url": VIDEO_PIPELINE_URL,
            "error": f"Timeout error: {str(e)}",
            "suggestion": "Video pipeline service is not responding"
        }
    except Exception as e:
        return {
            "status": "failed",
            "video_pipeline_url": VIDEO_PIPELINE_URL,
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/health/")
async def video_pipeline_health(client: httpx.AsyncClient = Depends(get_video_pipeline_client)):
    """Check video pipeline service health"""
    try:
        response = await client.get(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/health/")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Video pipeline service unavailable: {str(e)}")

@router.post("/camera/{camera_id}/video-info/")
async def get_camera_video_info(
    camera_id: int,
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """Get video information for a specific camera"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Forward request to video pipeline service
        files = {"video": (video.filename, video.file, video.content_type)}
        response = await client.post(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/video-info/", files=files)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video info: {str(e)}")

@router.post("/camera/{camera_id}/video-info-url/")
async def get_camera_video_info_url(
    camera_id: int,
    url: str = Form(...),
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """Get video information for a specific camera from URL"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Forward request to video pipeline service
        data = {"url": url}
        response = await client.post(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/video-info-url/", data=data)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video info: {str(e)}")

@router.post("/camera/{camera_id}/decode/")
async def decode_camera_video(
    camera_id: int,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    fps: Optional[int] = Form(1),
    force_format: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """Decode video for a specific camera"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Prepare form data
        data = {"fps": fps}
        if force_format:
            data["force_format"] = force_format
        if url:
            data["url"] = url
            
        files = {}
        if file:
            files["file"] = (file.filename, file.file, file.content_type)
        
        # Forward request to video pipeline service
        response = await client.post(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/", data=data, files=files)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to decode video: {str(e)}")

@router.post("/camera/{camera_id}/snapshot/")
async def capture_camera_snapshot(
    camera_id: int,
    video_url: str,
    timestamp: str,
    output_image: str,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """Capture snapshot from camera video"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Forward request to video pipeline service
        data = {
            "video_url": video_url,
            "timestamp": timestamp,
            "output_image": output_image
        }
        response = await client.post(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/snapshot/", json=data)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to capture snapshot: {str(e)}")

@router.post("/camera/{camera_id}/record/")
async def record_camera_clip(
    camera_id: int,
    video_url: str,
    start_time: str,
    duration: str,
    output_path: str,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_video_pipeline_client)
):
    """Record video clip from camera"""
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Forward request to video pipeline service
        data = {
            "video_url": video_url,
            "start_time": start_time,
            "duration": duration,
            "output_path": output_path
        }
        response = await client.post(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/record/", json=data)
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record clip: {str(e)}")

@router.get("/hw-accel-cap/")
async def get_hw_accel_capabilities(client: httpx.AsyncClient = Depends(get_video_pipeline_client)):
    """Get hardware acceleration capabilities"""
    try:
        response = await client.get(f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/hw-accel-cap/")
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hardware acceleration info: {str(e)}") 