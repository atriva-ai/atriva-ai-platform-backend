from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship

class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "People Counting", "Dwell Time", "Line Crossing"
    type = Column(String, nullable=False)  # e.g., "people_counting", "dwell_time", "line_crossing"
    config = Column(JSON, nullable=True)   # Store analytics-specific configuration
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship with cameras through the association table
    cameras = relationship("Camera", secondary="camera_analytics", back_populates="analytics")

    def __repr__(self):
        return f"<Analytics(id={self.id}, name='{self.name}', type='{self.type}')>" 