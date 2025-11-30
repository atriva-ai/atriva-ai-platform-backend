from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    analytics_id = Column(Integer, ForeignKey("analytics.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    camera = relationship("Camera", back_populates="zones")
    analytics = relationship("Analytics")

    def __repr__(self):
        return f"<Zone(id={self.id}, name='{self.name}', camera_id={self.camera_id}, analytics_id={self.analytics_id})>"
