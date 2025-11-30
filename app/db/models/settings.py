from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    store_name = Column(String, nullable=False)
    store_description = Column(String)
    store_timezone = Column(String, default="UTC")
    store_language = Column(String, default="en")
    store_theme = Column(String, default="light")
    store_notifications_enabled = Column(Boolean, default=True)
    store_analytics_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Settings(id={self.id}, store_name='{self.store_name}')>" 