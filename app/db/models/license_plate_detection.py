from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Boolean
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship

class LicensePlateDetection(Base):
    __tablename__ = "license_plate_detections"

    id = Column(Integer, primary_key=True, index=True)
    
    # Source information
    source_type = Column(String, nullable=False)  # "camera" or "file"
    source_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)  # camera_id for camera sources, null for file sources
    source_name = Column(String, nullable=False)  # camera name or filename
    
    # Detection details
    plate_number = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    
    # Image information
    thumbnail_path = Column(String, nullable=True)  # Path to thumbnail image
    full_image_path = Column(String, nullable=True)  # Path to full detection image
    
    # Detection metadata
    detection_bbox = Column(JSON, nullable=True)  # Bounding box coordinates [xmin, ymin, xmax, ymax]
    detection_results = Column(JSON, nullable=True)  # Full detection results from AI service
    
    # Video information (for file uploads)
    video_path = Column(String, nullable=True)  # Path to uploaded video file
    video_timestamp = Column(String, nullable=True)  # Timestamp in video where detection occurred
    start_time_offset = Column(String, nullable=True)  # User-specified start time offset
    
    # Location information
    location = Column(String, nullable=True)  # Physical location (for camera) or "File Upload" (for files)
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow)  # When detection was processed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<LicensePlateDetection(id={self.id}, plate_number='{self.plate_number}', source_type='{self.source_type}', source_name='{self.source_name}')>"
