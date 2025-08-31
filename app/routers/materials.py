from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.post("", response_model=schemas.MaterialRead, status_code=201)
def create_material(
    material: schemas.MaterialCreate, db: Session = Depends(get_db)
):
    mat = models.Material(**material.model_dump())
    db.add(mat)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Material name already exists")
    db.refresh(mat)
    return mat


@router.get("", response_model=list[schemas.MaterialRead])
def list_materials(
    search: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(models.Material)
    if search:
        q = q.filter(models.Material.name.ilike(f"%{search}%"))
    return q.order_by(models.Material.name).limit(limit).offset(offset).all()


@router.get("/{material_id}", response_model=schemas.MaterialRead)
def get_material(material_id: UUID, db: Session = Depends(get_db)):
    mat = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    return mat


@router.patch("/{material_id}", response_model=schemas.MaterialRead)
def update_material(
    material_id: UUID,
    material_up: schemas.MaterialUpdate,
    db: Session = Depends(get_db),
):
    mat = db.query(models.Material).filter(models.Material.id == material_id).first()
    if not mat:
        raise HTTPException(status_code=404, detail="Material not found")
    for field, value in material_up.model_dump(exclude_unset=True).items():
        setattr(mat, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Material name already exists")
    db.refresh(mat)
    return mat
