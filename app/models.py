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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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

    # JSONB: tags como lista de strings
    tags: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # JSONB: extra como objeto libre (dict)
    extra: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
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
