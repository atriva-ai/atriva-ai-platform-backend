from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship

class AlertEngine(Base):
    __tablename__ = "alert_engines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    type = Column(String, nullable=False)  # human_detection, human_crossing_line, human_in_zone
    config = Column(JSON, nullable=True)  # Store line/zone coordinates and other config
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Many-to-many relationship with cameras through association table
    cameras = relationship("Camera", secondary="camera_alert_engines", back_populates="alert_engines")

    def __repr__(self):
        return f"<AlertEngine(id={self.id}, name='{self.name}', type='{self.type}')>" 