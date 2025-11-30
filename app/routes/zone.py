from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.db.crud import zone as zone_crud
from app.db.schemas.zone import ZoneCreate, ZoneUpdate, Zone

router = APIRouter(
    prefix="/api/v1/zones",
    tags=["zones"]
)

@router.get("/", response_model=List[Zone])
def get_all_zones(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all zones"""
    return zone_crud.get_all_zones(db, skip=skip, limit=limit)

@router.post("/", response_model=Zone, status_code=status.HTTP_201_CREATED)
def create_zone(
    zone: ZoneCreate,
    db: Session = Depends(get_db)
):
    """Create a new zone"""
    # Check if zone name already exists
    if zone_crud.get_zone_by_name(db, zone.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone with this name already exists"
        )
    return zone_crud.create_zone(db, zone)

@router.get("/{zone_id}", response_model=Zone)
def get_zone(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific zone"""
    db_zone = zone_crud.get_zone(db, zone_id)
    if not db_zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )
    return db_zone

@router.put("/{zone_id}", response_model=Zone)
def update_zone(
    zone_id: int,
    zone: ZoneUpdate,
    db: Session = Depends(get_db)
):
    """Update a zone"""
    db_zone = zone_crud.update_zone(db, zone_id, zone)
    if not db_zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )
    return db_zone

@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """Delete a zone"""
    if not zone_crud.delete_zone(db, zone_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )

@router.patch("/{zone_id}/toggle", response_model=Zone)
def toggle_zone_active(
    zone_id: int,
    db: Session = Depends(get_db)
):
    """Toggle zone active status"""
    db_zone = zone_crud.toggle_zone_active(db, zone_id)
    if not db_zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found"
        )
    return db_zone

@router.get("/camera/{camera_id}", response_model=List[Zone])
def get_zones_by_camera(
    camera_id: int,
    db: Session = Depends(get_db)
):
    """Get all zones for a specific camera"""
    return zone_crud.get_zones_by_camera(db, camera_id)
