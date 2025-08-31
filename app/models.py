# app/models.py
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Any, List, Optional

from sqlalchemy import (
    String,
    Integer,
    Date,
    Text,
    ForeignKey,
    CheckConstraint,
    func,
    Index,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------
# Category (mínimo útil)
# ---------------------------
class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    # relación inversa opcional
    documents: Mapped[list["Document"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r}>"


# ---------------------------
# Document
# ---------------------------
class Document(Base):
    __tablename__ = "documents"

    # UUID generado en app (más portable que extensiones del server)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    date_ref: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # JSON: tags como lista de strings
    tags: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    # JSON: extra como objeto libre (dict)
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    # <- Campo que necesitabas persistir
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="vigente", index=True
    )

    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # relaciones
    category: Mapped["Category"] = relationship(back_populates="documents")

    __table_args__ = (
        # status opcionalmente restringido (ajustá los valores válidos si querés)
        CheckConstraint(
            "status in ('vigente','archivado','baja')",
            name="ck_documents_status",
        ),
        # Índices útiles para listados y filtros
        Index(
            "ix_documents_cat_status_date",
            "category_id",
            "status",
            "date_ref",
            postgresql_using="btree",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} title={self.title!r} "
            f"cat={self.category_id} date_ref={self.date_ref} status={self.status}>"
        )


# ---------------------------
# Material
# ---------------------------
class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    batches: Mapped[list["Batch"]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - repr simple
        return f"<Material id={self.id} name={self.name!r}>"


# ---------------------------
# Batch
# ---------------------------
class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    material_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_code: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(
        Integer, CheckConstraint("quantity >= 0"), nullable=False
    )
    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    material: Mapped["Material"] = relationship(back_populates="batches")

    __table_args__ = (
        UniqueConstraint("material_id", "batch_code", name="uq_batches_material_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover - repr simple
        return f"<Batch id={self.id} material_id={self.material_id} code={self.batch_code!r}>"
