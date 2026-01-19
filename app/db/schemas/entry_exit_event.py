from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EntryExitEventBase(BaseModel):
    camera_id: int = Field(..., description="Camera ID")
    event: str = Field(..., description="Event type: 'enter' or 'exit'")
    timestamp: datetime = Field(..., description="Event timestamp")
    track_id: int = Field(..., description="Track ID of the person")

class EntryExitEventCreate(EntryExitEventBase):
    pass

class EntryExitEvent(EntryExitEventBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

