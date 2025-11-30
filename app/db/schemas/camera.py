from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class CameraBase(BaseModel):
    name: str
    rtsp_url: str
    location: Optional[str] = None
    is_active: bool = False
    zone_ids: Optional[List[int]] = []
    # Vehicle tracking configuration
    vehicle_tracking_enabled: bool = False
    vehicle_tracking_config: Optional[Dict[str, Any]] = None

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None
    video_info: Optional[Dict[str, Any]] = None
    # Vehicle tracking configuration
    vehicle_tracking_enabled: Optional[bool] = None
    vehicle_tracking_config: Optional[Dict[str, Any]] = None

class CameraInDB(CameraBase):
    id: int
    video_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CameraOut(CameraBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class CameraRead(CameraBase):
    id: int
    analytics_config: Optional[Dict] = {}

    model_config = ConfigDict(from_attributes=True)
