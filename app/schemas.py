# app/schemas.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# Document Schemas
# ---------------------------------------------------------------------

class DocumentOut(BaseModel):
    """
    Esquema de salida para documentos.
    Compatible con SQLAlchemy usando from_attributes=True.
    """
    id: UUID
    title: str
    category_id: int
    date_ref: date
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None
    status: str
    current_version: int

    class Config:
        # Pydantic v2: habilita carga desde objetos ORM (SQLAlchemy)
        from_attributes = True


# (Opcional) Si más adelante exponés una actualización parcial vía PATCH
class DocumentPatch(BaseModel):
    """
    Campos opcionales para actualizar parcialmente un documento.
    No es usado por el POST multipart; sirve para futuros endpoints PATCH/PUT.
    """
    title: Optional[str] = None
    category_id: Optional[int] = None
    date_ref: Optional[date] = None
    tags: Optional[List[str]] = None
    extra: Optional[Dict[str, Any]] = None
    note: Optional[str] = None
    status: Optional[str] = None
    current_version: Optional[int] = None

    class Config:
        from_attributes = True


# (Opcional) En caso de que quieras un envoltorio de lista tipado
class DocumentList(BaseModel):
    """
    Envoltorio de lista por si querés un response model consistente
    (no es necesario si devolvés List[DocumentOut] directamente).
    """
    items: List[DocumentOut]
    total: int

    class Config:
        from_attributes = True
