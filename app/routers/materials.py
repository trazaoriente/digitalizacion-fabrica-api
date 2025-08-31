from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.post("", response_model=schemas.MaterialRead, status_code=201)
def create_material(material: schemas.MaterialCreate, db: Session = Depends(get_db)):
    obj = models.Material(**material.model_dump())
    db.add(obj)
    try:
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Material name already exists")
    return obj


@router.get("", response_model=list[schemas.MaterialRead])
def list_materials(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="Search by name"),
    is_active: bool | None = Query(True, description="Filter by active flag"),
):
    q = db.query(models.Material)
    if search:
        q = q.filter(models.Material.name.ilike(f"%{search}%"))
    if is_active is not None:
        q = q.filter(models.Material.is_active == is_active)
    return q.order_by(models.Material.name).all()


@router.get("/{material_id}", response_model=schemas.MaterialRead)
def get_material(material_id: str, db: Session = Depends(get_db)):
    obj = db.get(models.Material, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    return obj


@router.put("/{material_id}", response_model=schemas.MaterialRead)
def update_material(
    material_id: str,
    material_in: schemas.MaterialUpdate,
    db: Session = Depends(get_db),
):
    obj = db.get(models.Material, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    for key, value in material_in.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Material name already exists")
    db.refresh(obj)
    return obj


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: str, db: Session = Depends(get_db)):
    obj = db.get(models.Material, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material not found")
    obj.is_active = False
    db.commit()
    return None
