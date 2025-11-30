from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from .analytics import Analytics

class ZoneBase(BaseModel):
    name: str = Field(..., description="Name of the zone")
    camera_id: int = Field(..., description="ID of the camera this zone belongs to")
    analytics_id: int = Field(..., description="ID of the analytics configuration for this zone")
    is_active: bool = Field(True, description="Whether the zone is active")

class ZoneCreate(ZoneBase):
    pass

class ZoneUpdate(ZoneBase):
    name: Optional[str] = None
    camera_id: Optional[int] = None
    analytics_id: Optional[int] = None
    is_active: Optional[bool] = None

class ZoneInDB(ZoneBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Zone(ZoneInDB):
    analytics: Optional[Analytics] = None
