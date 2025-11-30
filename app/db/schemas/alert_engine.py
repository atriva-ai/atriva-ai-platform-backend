from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from .camera import CameraInDB

class AlertEngineBase(BaseModel):
    name: str = Field(..., description="Name of the alert engine")
    type: str = Field(..., description="Type of alert engine (human_detection, human_crossing_line, human_in_zone)")
    config: Optional[Dict[str, Any]] = Field(None, description="Configuration data (line/zone coordinates, etc.)")
    is_active: bool = Field(True, description="Whether the alert engine is active")

class AlertEngineCreate(AlertEngineBase):
    pass

class AlertEngineUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class AlertEngineInDB(AlertEngineBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime

class AlertEngine(AlertEngineInDB):
    cameras: Optional[List[CameraInDB]] = None

class CameraAlertEngineCreate(BaseModel):
    camera_id: int = Field(..., description="ID of the camera")
    alert_engine_id: int = Field(..., description="ID of the alert engine") 