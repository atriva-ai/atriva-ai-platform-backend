from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime

class AnalyticsBase(BaseModel):
    name: str = Field(..., description="Name of the analytics (e.g., 'People Counting')")
    type: str = Field(..., description="Type of analytics (e.g., 'people_counting')")
    config: Optional[Dict[str, Any]] = Field(None, description="Analytics-specific configuration")
    is_active: bool = Field(True, description="Whether the analytics is active")

class AnalyticsCreate(AnalyticsBase):
    pass

class AnalyticsUpdate(AnalyticsBase):
    name: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None

class AnalyticsInDB(AnalyticsBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Analytics(AnalyticsInDB):
    pass

# Schema for camera-analytics relationship
class CameraAnalytics(BaseModel):
    camera_id: int
    analytics_id: int

class CameraAnalyticsCreate(CameraAnalytics):
    pass

class CameraAnalyticsUpdate(CameraAnalytics):
    pass

class CameraAnalyticsInDB(CameraAnalytics):
    model_config = ConfigDict(from_attributes=True) 