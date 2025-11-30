from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class LicensePlateDetectionBase(BaseModel):
    source_type: str = Field(..., description="Source type: 'camera' or 'file'")
    source_id: Optional[int] = Field(None, description="Camera ID for camera sources")
    source_name: str = Field(..., description="Camera name or filename")
    plate_number: str = Field(..., description="Detected license plate number")
    confidence: float = Field(..., description="Detection confidence score")
    thumbnail_path: Optional[str] = Field(None, description="Path to thumbnail image")
    full_image_path: Optional[str] = Field(None, description="Path to full detection image")
    detection_bbox: Optional[List[float]] = Field(None, description="Bounding box coordinates [xmin, ymin, xmax, ymax]")
    detection_results: Optional[Dict[str, Any]] = Field(None, description="Full detection results from AI service")
    video_path: Optional[str] = Field(None, description="Path to uploaded video file")
    video_timestamp: Optional[str] = Field(None, description="Timestamp in video where detection occurred")
    start_time_offset: Optional[str] = Field(None, description="User-specified start time offset")
    location: Optional[str] = Field(None, description="Physical location or 'File Upload'")
    is_active: bool = Field(True, description="Whether detection is active")

class LicensePlateDetectionCreate(LicensePlateDetectionBase):
    pass

class LicensePlateDetectionUpdate(BaseModel):
    plate_number: Optional[str] = None
    confidence: Optional[float] = None
    thumbnail_path: Optional[str] = None
    full_image_path: Optional[str] = None
    detection_bbox: Optional[List[float]] = None
    detection_results: Optional[Dict[str, Any]] = None
    video_path: Optional[str] = None
    video_timestamp: Optional[str] = None
    start_time_offset: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

class LicensePlateDetection(LicensePlateDetectionBase):
    id: int
    detected_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FileUploadRequest(BaseModel):
    filename: str = Field(..., description="Name of the uploaded file")
    start_time_offset: Optional[str] = Field(None, description="Start time offset in format 'HH:MM:SS' or 'MM:SS'")
    location: Optional[str] = Field("File Upload", description="Location identifier for the file")

class FileUploadResponse(BaseModel):
    file_id: str = Field(..., description="Unique identifier for the uploaded file")
    filename: str = Field(..., description="Name of the uploaded file")
    video_path: str = Field(..., description="Path where the video file is stored")
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="Status message")
