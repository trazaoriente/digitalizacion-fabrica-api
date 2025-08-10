# app/routers/documents.py
from __future__ import annotations

import json
import os
import uuid
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/documents", tags=["documents"])

# --- Opcional: guardado efímero del archivo en disco (Render es efímero) ---
UPLOAD_DIR = "/tmp/uploads"

def _save_upload_temporarily(file: UploadFile) -> str:
    """
    Guarda el archivo en /tmp/uploads y devuelve la ruta.
    Útil para depurar. En producción, reemplazar por S3/Backblaze/etc.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{file.filename}".replace(os.sep, "_")
    dest_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(dest_path, "wb") as out:
        out.write(file.file.read())
    # reset pointer por si alguien vuelve a leer
    file.file.seek(0)
    return dest_path


@router.post(
    "",
    response_model=schemas.DocumentOut,
    status_code=201,
    summary="Crear documento (multipart/form-data)",
)
async def create_document(
    file: UploadFile = File(..., description="Archivo PDF u otro"),
    title: str = Form(..., description="Título del documento"),
    category_id: int = Form(..., description="ID de categoría"),
    date_ref: date = Form(..., description="Fecha de referencia (YYYY-MM-DD)"),
    tags: str = Form("", description="Tags separados por coma, ej: 'poes,enjuagadora,qa'"),
    extra: str = Form("{}", description="Objeto JSON en texto"),
    note: Optional[str] = Form(None, description="Nota opcional"),
    db: Session = Depends(get_db),
):
    # Parseo/normalización de tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Parseo de extra (JSON)
    try:
        extra_obj = json.loads(extra) if isinstance(extra, str) else (extra or {})
        if not isinstance(extra_obj, dict):
            raise ValueError("extra debe ser un objeto JSON")
    except Exception:
        raise HTTPException(status_code=422, detail="Campo 'extra' no es JSON válido (objeto)")

    # (Opcional) Guardar temporalmente el archivo para auditar
    # En producción, reemplazar por servicio de storage y guardar solo la URL/clave.
    try:
        _ = _save_upload_temporarily(file)
    except Exception as e:
        # No bloquea la creación del registro si falla el guardado efímero
        # pero podés cambiar esto si querés hacerlo obligatorio.
        print(f"[WARN] No se pudo guardar temporalmente el archivo: {e}")

    # Crear entidad
    doc = models.Document(
        title=title,
        category_id=category_id,
        date_ref=date_ref,
        tags=tag_list,
        extra=extra_obj,
        note=note,                 # <-- clave: que se asigne y persista
        status="vigente",
        current_version=1,
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get(
    "/{document_id}",
    response_model=schemas.DocumentOut,
    summary="Obtener documento por ID",
)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc


@router.get(
    "",
    response_model=List[schemas.DocumentOut],
    summary="Listar documentos (paginado)",
)
def list_documents(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Cantidad a devolver"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginado"),
    status: Optional[str] = Query(None, description="Filtrar por estado, ej: 'vigente'"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoría"),
):
    q = db.query(models.Document)
    if status:
        q = q.filter(models.Document.status == status)
    if category_id is not None:
        q = q.filter(models.Document.category_id == category_id)
    return q.order_by(models.Document.date_ref.desc(), models.Document.id.desc()).limit(limit).offset(offset).all()
