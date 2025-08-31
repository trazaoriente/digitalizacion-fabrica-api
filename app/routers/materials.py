from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.post("/", response_model=schemas.MaterialRead, status_code=201)
def create_material(material: schemas.MaterialCreate, db: Session = Depends(get_db)):
    obj = models.Material(**material.model_dump())
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Material name duplicado")
    db.refresh(obj)
    return obj


@router.get("/{material_id}", response_model=schemas.MaterialRead)
def get_material(material_id: str, db: Session = Depends(get_db)):
    obj = db.get(models.Material, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    return obj


@router.get("/", response_model=list[schemas.MaterialRead])
def list_materials(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="Filtro por nombre/descripcion"),
    is_active: bool | None = Query(True, description="Filtrar por activos"),
):
    q = db.query(models.Material)
    if search:
        pattern = f"%{search.lower()}%"
        q = q.filter(
            or_(
                func.lower(models.Material.name).like(pattern),
                func.lower(models.Material.description).like(pattern),
            )
        )
    if is_active is not None:
        q = q.filter(models.Material.is_active == is_active)
    return q.order_by(models.Material.name).all()


@router.put("/{material_id}", response_model=schemas.MaterialRead)
def update_material(
    material_id: str, payload: schemas.MaterialUpdate, db: Session = Depends(get_db)
):
    obj = db.get(models.Material, material_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Material name duplicado")
    db.refresh(obj)
    return obj


@router.delete("/{material_id}", status_code=204)
def delete_material(material_id: str, db: Session = Depends(get_db)):
    obj = db.get(models.Material, material_id)
    if not obj or not obj.is_active:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    obj.is_active = False
    db.commit()
    return None
