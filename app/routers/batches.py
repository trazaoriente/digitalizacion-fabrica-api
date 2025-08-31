from __future__ import annotations

from datetime import date
from uuid import UUID

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
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Batch already exists")
    db.refresh(obj)
    return obj


@router.get("", response_model=list[schemas.BatchRead])
def list_batches(
    material_id: UUID | None = None,
    batch_code: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
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
    return (
        q.order_by(models.Batch.production_date.desc(), models.Batch.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.get("/{batch_id}", response_model=schemas.BatchRead)
def get_batch(batch_id: UUID, db: Session = Depends(get_db)):
    obj = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Batch not found")
    return obj


@router.patch("/{batch_id}", response_model=schemas.BatchRead)
def update_batch(
    batch_id: UUID,
    batch_up: schemas.BatchUpdate,
    db: Session = Depends(get_db),
):
    obj = db.query(models.Batch).filter(models.Batch.id == batch_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Batch not found")
    for field, value in batch_up.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Batch already exists")
    db.refresh(obj)
    return obj
