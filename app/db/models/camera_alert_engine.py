from sqlalchemy import Column, Integer, ForeignKey, Table
from app.database import Base

# Association table for many-to-many relationship between cameras and alert engines
camera_alert_engines = Table(
    "camera_alert_engines",
    Base.metadata,
    Column("camera_id", Integer, ForeignKey("cameras.id"), primary_key=True),
    Column("alert_engine_id", Integer, ForeignKey("alert_engines.id"), primary_key=True)
) 