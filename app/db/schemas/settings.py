from pydantic import BaseModel, EmailStr, HttpUrl, ConfigDict
from typing import Optional
from datetime import datetime

class SettingsBase(BaseModel):
    store_name: str
    store_description: Optional[str] = None
    store_timezone: str = "UTC"
    store_language: str = "en"
    store_theme: str = "light"
    store_notifications_enabled: bool = True
    store_analytics_enabled: bool = True

class SettingsCreate(SettingsBase):
    pass

class SettingsUpdate(BaseModel):
    store_name: Optional[str] = None
    store_description: Optional[str] = None
    store_timezone: Optional[str] = None
    store_language: Optional[str] = None
    store_theme: Optional[str] = None
    store_notifications_enabled: Optional[bool] = None
    store_analytics_enabled: Optional[bool] = None

class SettingsResponse(SettingsBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) 