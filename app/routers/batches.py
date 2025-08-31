from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter()


@router.post("", response_model=schemas.BatchRead, status_code=201)
def create_batch(batch: schemas.BatchCreate, db: Session = Depends(get_db)):
    obj = models.Batch(**batch.model_dump())
    db.add(obj)
    try:
        db.commit()
        db.refresh(obj)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Batch already exists")
    return obj


@router.get("", response_model=list[schemas.BatchRead])
def list_batches(
    db: Session = Depends(get_db),
    material_id: str | None = Query(None),
    batch_code: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    is_active: bool | None = Query(True),
):
    q = db.query(models.Batch)
    if material_id:
        q = q.filter(models.Batch.material_id == material_id)
    if batch_code:
        q = q.filter(models.Batch.batch_code == batch_code)
    if date_from:
        q = q.filter(models.Batch.production_date >= date_from)
    if date_to:
        q = q.filter(models.Batch.production_date <= date_to)
    if is_active is not None:
        q = q.filter(models.Batch.is_active == is_active)
    return q.order_by(models.Batch.production_date.desc()).all()


@router.get("/{batch_id}", response_model=schemas.BatchRead)
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    obj = db.get(models.Batch, batch_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Batch not found")
    return obj


@router.put("/{batch_id}", response_model=schemas.BatchRead)
def update_batch(batch_id: str, batch_in: schemas.BatchUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Batch, batch_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Batch not found")
    for key, value in batch_in.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Batch already exists")
    db.refresh(obj)
    return obj


@router.delete("/{batch_id}", status_code=204)
def delete_batch(batch_id: str, db: Session = Depends(get_db)):
    obj = db.get(models.Batch, batch_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Batch not found")
    obj.is_active = False
    db.commit()
    return None
