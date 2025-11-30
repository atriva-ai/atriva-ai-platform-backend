# routers/store.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.models.store import Store
from app.db.schemas.store import StoreSchema, StoreResponse
from app.dependencies import get_db

router = APIRouter()

# Request schema
class StoreUpdate(BaseModel):
    name: str

@router.get("/", response_model=StoreResponse)
def get_store(db: Session = Depends(get_db)):
    store = db.query(Store).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return {"name": store.name}

@router.post("/", response_model=StoreResponse)
def set_store_name(store_data: StoreSchema, db: Session = Depends(get_db)):
    store = db.query(Store).first()
    if not store:
        store = Store(name=store_data.name)
        db.add(store)
    else:
        store.name = store_data.name
    db.commit()
    db.refresh(store)
    return {"name": store.name}