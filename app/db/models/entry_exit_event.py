from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.database import Base

class EntryExitEvent(Base):
    __tablename__ = "entry_exit_events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    event = Column(String, nullable=False)  # "enter" or "exit"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    track_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EntryExitEvent(id={self.id}, camera_id={self.camera_id}, event='{self.event}', track_id={self.track_id})>"

