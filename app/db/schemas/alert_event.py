from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any, Dict
from datetime import datetime

class AlertEventBase(BaseModel):
    camera_id: int
    alert_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    ai_annotation_path: Optional[str] = None
    detection_results: Optional[Any] = None

class AlertEventCreate(AlertEventBase):
    pass

class AlertEventUpdate(BaseModel):
    end_time: Optional[datetime] = None
    ai_annotation_path: Optional[str] = None
    detection_results: Optional[Any] = None

class AlertEventInDB(AlertEventBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime

class AlertEvent(AlertEventInDB):
    pass 