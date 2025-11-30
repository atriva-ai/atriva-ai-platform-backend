from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.db.utils import should_defer_vehicle_tracking

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
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to handle missing vehicle tracking attributes gracefully"""
        # If vehicle tracking columns don't exist, set defaults using getattr
        if should_defer_vehicle_tracking():
            # Use getattr with sentinel to check without triggering lazy load
            _sentinel = object()
            if getattr(obj, 'vehicle_tracking_enabled', _sentinel) is _sentinel:
                setattr(obj, 'vehicle_tracking_enabled', False)
            if getattr(obj, 'vehicle_tracking_config', _sentinel) is _sentinel:
                setattr(obj, 'vehicle_tracking_config', None)
        return super().model_validate(obj, **kwargs)

class CameraOut(CameraBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to handle missing vehicle tracking attributes gracefully"""
        # If vehicle tracking columns don't exist, set defaults using getattr
        if should_defer_vehicle_tracking():
            # Use getattr with sentinel to check without triggering lazy load
            _sentinel = object()
            if getattr(obj, 'vehicle_tracking_enabled', _sentinel) is _sentinel:
                setattr(obj, 'vehicle_tracking_enabled', False)
            if getattr(obj, 'vehicle_tracking_config', _sentinel) is _sentinel:
                setattr(obj, 'vehicle_tracking_config', None)
        return super().model_validate(obj, **kwargs)

class CameraRead(CameraBase):
    id: int
    analytics_config: Optional[Dict] = {}

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to handle missing vehicle tracking attributes gracefully"""
        # If vehicle tracking columns don't exist, set defaults using getattr
        if should_defer_vehicle_tracking():
            # Use getattr with sentinel to check without triggering lazy load
            _sentinel = object()
            if getattr(obj, 'vehicle_tracking_enabled', _sentinel) is _sentinel:
                setattr(obj, 'vehicle_tracking_enabled', False)
            if getattr(obj, 'vehicle_tracking_config', _sentinel) is _sentinel:
                setattr(obj, 'vehicle_tracking_config', None)
        return super().model_validate(obj, **kwargs)
