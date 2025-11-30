# models/store.py
from sqlalchemy import Column, Integer, String
from app.database import Base  # this should be your declarative base

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
