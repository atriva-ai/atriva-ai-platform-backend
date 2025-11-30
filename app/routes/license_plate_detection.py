from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import asyncio
import httpx
from datetime import datetime, timedelta

from app.database import get_db
from app.db.schemas.license_plate_detection import (
    LicensePlateDetection, 
    LicensePlateDetectionCreate, 
    LicensePlateDetectionUpdate,
    FileUploadRequest,
    FileUploadResponse
)
from app.db.crud import license_plate_detection as detection_crud
from app.db.models.camera import Camera
from app.db.crud import camera as camera_crud

router = APIRouter(
    prefix="/api/v1/license-plates",
    tags=["License Plate Detection"]
)

# Service URLs
AI_INFERENCE_URL = os.getenv("AI_INFERENCE_URL", "http://ai_inference:8001")
VIDEO_PIPELINE_URL = os.getenv("VIDEO_PIPELINE_URL", "http://video_pipeline:8002")

# File upload configuration
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def get_ai_inference_client():
    """Get HTTP client for AI inference service"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        yield client

@router.get("/", response_model=List[LicensePlateDetection])
def get_license_plate_detections(
    skip: int = 0,
    limit: int = 100,
    source_type: Optional[str] = None,
    plate_number: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get license plate detections with optional filters"""
    return detection_crud.get_license_plate_detections(
        db, skip=skip, limit=limit, 
        source_type=source_type, 
        plate_number=plate_number, 
        is_active=is_active
    )

@router.get("/{detection_id}", response_model=LicensePlateDetection)
def get_license_plate_detection(detection_id: int, db: Session = Depends(get_db)):
    """Get a specific license plate detection"""
    detection = detection_crud.get_license_plate_detection(db, detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection

@router.get("/plate/{plate_number}", response_model=List[LicensePlateDetection])
def get_detections_by_plate_number(plate_number: str, db: Session = Depends(get_db)):
    """Get all detections for a specific license plate number"""
    return detection_crud.get_detections_by_plate_number(db, plate_number)

@router.get("/source/{source_type}", response_model=List[LicensePlateDetection])
def get_detections_by_source(
    source_type: str, 
    source_id: Optional[int] = None, 
    db: Session = Depends(get_db)
):
    """Get detections by source type and optionally source ID"""
    return detection_crud.get_detections_by_source(db, source_type, source_id)

@router.get("/repeated/{timeframe_hours}", response_model=List[dict])
def get_repeated_plates(timeframe_hours: int = 24, db: Session = Depends(get_db)):
    """Get license plates that appear multiple times within a timeframe"""
    return detection_crud.get_repeated_plates(db, timeframe_hours)

@router.post("/upload-file", response_model=FileUploadResponse)
async def upload_video_file(
    file: UploadFile = File(...),
    start_time_offset: Optional[str] = Form(None),
    location: Optional[str] = Form("File Upload"),
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_ai_inference_client)
):
    """Upload a video file for license plate detection"""
    
    print(f"🚀 UPLOAD START: Received file '{file.filename}' ({file.size} bytes)")
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('video/'):
        print(f"❌ VALIDATION FAILED: Invalid file type '{file.content_type}'")
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Validate file size (max 500MB)
    max_size = 500 * 1024 * 1024  # 500MB
    if file.size and file.size > max_size:
        file_size_mb = file.size / (1024 * 1024)
        print(f"❌ VALIDATION FAILED: File too large ({file_size_mb:.1f}MB)")
        raise HTTPException(
            status_code=400, 
            detail=f"File too large: {file_size_mb:.1f}MB. Maximum allowed size is 500MB."
        )
    
    print(f"✅ VALIDATION PASSED: File type and size OK")
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    print(f"📁 SAVING FILE: {file_path}")
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"✅ FILE SAVED: {len(content)} bytes written to {file_path}")
        
        # Process video for license plate detection
        print(f"🎬 STARTING PROCESSING: Calling process_video_for_license_plates")
        await process_video_for_license_plates(
            file_path=file_path,
            filename=file.filename,
            start_time_offset=start_time_offset,
            location=location,
            db=db,
            client=client
        )
        
        print(f"🎉 PROCESSING COMPLETE: Video processed successfully")
        
        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            video_path=file_path,
            status="success",
            message="Video uploaded and processed successfully"
        )
        
    except Exception as e:
        print(f"💥 PROCESSING ERROR: {str(e)}")
        # Clean up file if processing fails
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🧹 CLEANUP: Removed file {file_path}")
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")

async def process_video_for_license_plates(
    file_path: str,
    filename: str,
    start_time_offset: Optional[str],
    location: str,
    db: Session,
    client: httpx.AsyncClient
):
    """Process uploaded video for license plate detection"""
    
    # Generate unique camera_id for this file upload
    file_camera_id = f"file_{str(uuid.uuid4())[:8]}"
    
    print(f"🎥 VIDEO PIPELINE: Generated camera_id: {file_camera_id}")
    
    try:
        # Step 1: Send video to video pipeline for frame extraction
        print(f"📤 SENDING TO VIDEO PIPELINE: {filename} -> {VIDEO_PIPELINE_URL}")
        
        # Prepare the video file for upload to video pipeline
        with open(file_path, "rb") as video_file:
            files = {"file": (filename, video_file, "video/mp4")}
            data = {
                "camera_id": file_camera_id,
                "fps": 1  # 1 frame per second as requested
            }
            
            print(f"📋 REQUEST DATA: camera_id={file_camera_id}, fps=1")
            
            # Send to video pipeline
            print(f"🌐 MAKING REQUEST TO: {VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/")
            response = await client.post(
                f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/",
                files=files,
                data=data
            )
            
            print(f"📡 VIDEO PIPELINE RESPONSE: Status {response.status_code}")
            print(f"📡 RESPONSE HEADERS: {dict(response.headers)}")
            
            if response.status_code != 200:
                try:
                    error_text = response.text
                    print(f"❌ VIDEO PIPELINE ERROR TEXT: {error_text}")
                except Exception as e:
                    error_text = f"Could not read response text: {str(e)}"
                    print(f"❌ ERROR READING RESPONSE: {error_text}")
                
                raise HTTPException(status_code=500, detail=f"Video pipeline decode failed: {error_text}")
            
            decode_result = response.json()
            print(f"✅ VIDEO DECODE STARTED: {decode_result}")
        
        # Step 2: Wait for frames to be extracted and process them
        print(f"⏳ WAITING FOR FRAMES: Starting frame processing")
        await process_extracted_frames(
            file_camera_id=file_camera_id,
            filename=filename,
            start_time_offset=start_time_offset,
            location=location,
            db=db,
            client=client
        )
        
    except Exception as e:
        print(f"💥 VIDEO PROCESSING ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")

async def process_extracted_frames(
    file_camera_id: str,
    filename: str,
    start_time_offset: Optional[str],
    location: str,
    db: Session,
    client: httpx.AsyncClient
):
    """Process extracted frames for license plate detection"""
    
    max_wait_time = 300  # 5 minutes max wait
    check_interval = 5   # Check every 5 seconds
    elapsed_time = 0
    
    print(f"Waiting for frames to be extracted for camera_id: {file_camera_id}")
    
    # Wait for frames to be available
    while elapsed_time < max_wait_time:
        try:
            # Check decode status
            status_response = await client.get(
                f"{VIDEO_PIPELINE_URL}/api/v1/video-pipeline/decode/status/?camera_id={file_camera_id}"
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Decode status: {status_data}")
                
                if status_data.get("status") == "completed" and status_data.get("frame_count", 0) > 0:
                    print(f"Frames ready! Processing {status_data['frame_count']} frames")
                    break
                elif status_data.get("status") == "running":
                    print(f"Still decoding... frame_count: {status_data.get('frame_count', 0)}")
                elif status_data.get("status") == "error":
                    raise HTTPException(status_code=500, detail=f"Video decode failed: {status_data.get('last_error', 'Unknown error')}")
            
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
            
        except Exception as e:
            print(f"Error checking decode status: {str(e)}")
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
    
    if elapsed_time >= max_wait_time:
        raise HTTPException(status_code=500, detail="Timeout waiting for video frames to be extracted")
    
    # Step 3: Run AI inference on frames
    await run_ai_inference_on_frames(
        file_camera_id=file_camera_id,
        filename=filename,
        start_time_offset=start_time_offset,
        location=location,
        db=db,
        client=client
    )

async def run_ai_inference_on_frames(
    file_camera_id: str,
    filename: str,
    start_time_offset: Optional[str],
    location: str,
    db: Session,
    client: httpx.AsyncClient
):
    """Run AI inference on extracted frames"""
    
    try:
        # Run license plate detection on the latest frame
        print(f"Running AI inference for license plate detection on camera_id: {file_camera_id}")
        
        inference_response = await client.post(
            f"{AI_INFERENCE_URL}/shared/cameras/{file_camera_id}/inference",
            data={"object_name": "license_plate"}
        )
        
        if inference_response.status_code != 200:
            print(f"AI inference failed: {inference_response.text}")
            # Create a record indicating no detections found
            detection_data = LicensePlateDetectionCreate(
                source_type="file",
                source_name=filename,
                plate_number="NO_DETECTION",
                confidence=0.0,
                thumbnail_path="",
                full_image_path="",
                detection_bbox=[],
                detection_results={"error": "AI inference failed", "status_code": inference_response.status_code},
                video_path="",
                video_timestamp=start_time_offset or "00:00:00",
                start_time_offset=start_time_offset,
                location=location
            )
            detection_crud.create_license_plate_detection(db, detection_data)
            return
        
        inference_result = inference_response.json()
        print(f"AI inference result: {inference_result}")
        
        detections = inference_result.get("detections", [])
        
        if not detections:
            # No license plates detected
            detection_data = LicensePlateDetectionCreate(
                source_type="file",
                source_name=filename,
                plate_number="NO_PLATES_FOUND",
                confidence=0.0,
                thumbnail_path="",
                full_image_path="",
                detection_bbox=[],
                detection_results={"message": "No license plates detected in video"},
                video_path="",
                video_timestamp=start_time_offset or "00:00:00",
                start_time_offset=start_time_offset,
                location=location
            )
            detection_crud.create_license_plate_detection(db, detection_data)
        else:
            # Process each detection
            for detection in detections:
                plate_number = detection.get("class_name", "UNKNOWN")
                confidence = detection.get("confidence", 0.0)
                bbox = detection.get("bbox", [])
                
                detection_data = LicensePlateDetectionCreate(
                    source_type="file",
                    source_name=filename,
                    plate_number=plate_number,
                    confidence=confidence,
                    thumbnail_path=inference_result.get("frame_path", ""),
                    full_image_path=inference_result.get("frame_path", ""),
                    detection_bbox=bbox,
                    detection_results=detection,
                    video_path="",
                    video_timestamp=start_time_offset or "00:00:00",
                    start_time_offset=start_time_offset,
                    location=location
                )
                detection_crud.create_license_plate_detection(db, detection_data)
        
        print(f"Successfully processed {len(detections)} license plate detections")
        
    except Exception as e:
        print(f"Error running AI inference: {str(e)}")
        # Create error record
        detection_data = LicensePlateDetectionCreate(
            source_type="file",
            source_name=filename,
            plate_number="PROCESSING_ERROR",
            confidence=0.0,
            thumbnail_path="",
            full_image_path="",
            detection_bbox=[],
            detection_results={"error": str(e)},
            video_path="",
            video_timestamp=start_time_offset or "00:00:00",
            start_time_offset=start_time_offset,
            location=location
        )
        detection_crud.create_license_plate_detection(db, detection_data)

@router.post("/camera/{camera_id}/detect", response_model=LicensePlateDetection)
async def detect_license_plates_from_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_ai_inference_client)
):
    """Run license plate detection on latest camera frame"""
    
    # Verify camera exists
    camera = camera_crud.get_camera(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        # Get latest frame from camera
        response = await client.post(f"{AI_INFERENCE_URL}/shared/cameras/{camera_id}/inference", 
                                   data={"object_name": "license_plate"})
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get camera frame")
        
        detection_data = response.json()
        
        # Create detection record
        detection_create = LicensePlateDetectionCreate(
            source_type="camera",
            source_id=camera_id,
            source_name=camera.name,
            plate_number="CAMERA123",  # This would come from actual detection
            confidence=0.90,
            thumbnail_path="/app/uploads/thumbnails/camera_thumb.jpg",
            full_image_path="/app/uploads/detections/camera_full.jpg",
            detection_bbox=[120, 140, 220, 170],
            detection_results=detection_data,
            location=camera.location or "Camera"
        )
        
        return detection_crud.create_license_plate_detection(db, detection_create)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect license plates: {str(e)}")

@router.put("/{detection_id}", response_model=LicensePlateDetection)
def update_license_plate_detection(
    detection_id: int,
    detection_update: LicensePlateDetectionUpdate,
    db: Session = Depends(get_db)
):
    """Update a license plate detection"""
    detection = detection_crud.update_license_plate_detection(db, detection_id, detection_update)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection

@router.delete("/{detection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_license_plate_detection(detection_id: int, db: Session = Depends(get_db)):
    """Delete a license plate detection"""
    success = detection_crud.delete_license_plate_detection(db, detection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Detection not found")
    return None
