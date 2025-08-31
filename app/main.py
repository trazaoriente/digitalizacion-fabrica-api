# app/main.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID
import hashlib, json, re, uuid, os

from supabase import create_client, Client
from app.config import settings
from app import models  # registra modelos en Base.metadata
from app.routers import materials, batches

# --------------------
# App & CORS
# --------------------
app = FastAPI(title="Digitalizacion Fabrica - API (Simulacro)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOW_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------
# Supabase client
# --------------------
sb: Optional[Client] = None
BUCKET = settings.SUPABASE_BUCKET or "traza-docs"
if settings.SUPABASE_ENABLED:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE:
        raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE")
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE)


def ensure_supabase() -> Client:
    if sb is None:
        raise HTTPException(status_code=503, detail="Supabase deshabilitado")
    return sb


# --------------------
# Startup DB / Routers
# --------------------


@app.on_event("startup")
def startup_event() -> None:
    # Intentar migrar con Alembic; SIEMPRE asegurar tablas con create_all
    try:
        from alembic import command
        from alembic.config import Config
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Alembic upgrade falló: %s", e)
    finally:
        from app.database import Base, engine
        Base.metadata.create_all(bind=engine)  # crea lo que falte, idempotente


app.include_router(materials.router, prefix="/materials", tags=["materials"])
app.include_router(batches.router, prefix="/batches", tags=["batches"])

# --------------------
# Utils
# --------------------
SAFE_CHARS = re.compile(r"[^a-zA-Z0-9._-]+")

def safe_filename(name: str) -> str:
    name = (name or "").strip().replace(" ", "_")
    return SAFE_CHARS.sub("_", name) or "archivo"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

# --------------------
# Schemas
# --------------------
class DocumentIn(BaseModel):
    title: str
    category_id: Optional[int] = None
    date_ref: Optional[date] = None
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None

class DocumentOut(DocumentIn):
    id: UUID
    status: str = "vigente"
    current_version: int = 1

class DocumentListOut(BaseModel):
    items: List[DocumentOut]
    total: int

# --------------------
# Endpoints
# --------------------
@app.get("/health")
def health():
    return {"ok": True}

@app.post("/documents", response_model=DocumentOut)
async def create_document(
    title: str = Form(...),
    category_id: Optional[int] = Form(None),
    date_ref: Optional[date] = Form(None),
    tags: Optional[str] = Form(None),   # CSV "a,b,c"
    extra: Optional[str] = Form(None),  # JSON string
    note: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    """
    Crea un documento (v1) + sube archivo a Supabase Storage (privado).
    """
    ensure_supabase()
    try:
        # Parse de campos
        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        try:
            extra_dict = json.loads(extra) if extra else {}
            if not isinstance(extra_dict, dict):
                raise ValueError("extra debe ser un objeto JSON")
        except Exception as je:
            raise HTTPException(status_code=422, detail=f"Campo 'extra' debe ser JSON válido: {je}")

        # IDs y ruta de almacenamiento
        doc_id = str(uuid.uuid4())
        version = 1
        filename = safe_filename(file.filename or "archivo")
        storage_path = f"{doc_id}/v{version}/{filename}"

        # Subir a Storage
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Archivo vacío")
        checksum = sha256_bytes(content)
        mime_type = file.content_type or "application/octet-stream"

        up_res = sb.storage.from_(BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": mime_type, "x-upsert": "false"},
        )
        # Algunos SDK devuelven dict con 'error'
        if isinstance(up_res, dict) and up_res.get("error"):
            raise HTTPException(status_code=500, detail=f"Error subiendo a Storage: {up_res['error']}")

        # Insertar en documents
        doc_payload = {
            "id": doc_id,
            "title": title,
            "category_id": category_id,
            "status": "vigente",
            "current_version": version,
            "date_ref": str(date_ref) if date_ref else None,
            "tags": tags_list,
            "extra": extra_dict,
            "created_by": None,  # opcional: enlazar con auth.uid()
        }
        ins_doc = sb.table("documents").insert(doc_payload).execute()
        if not getattr(ins_doc, "data", None):
            # rollback del archivo si la DB no insertó
            sb.storage.from_(BUCKET).remove([storage_path])
            raise HTTPException(status_code=500, detail="DB no devolvió datos al insertar documento")

        # Insertar en document_versions
        ver_payload = {
            "document_id": doc_id,
            "version": version,
            "storage_path": storage_path,
            "checksum": checksum,
            "size_bytes": len(content),
            "mime_type": mime_type,
            "note": note,
            "created_by": None,
        }
        ins_ver = sb.table("document_versions").insert(ver_payload).execute()
        if not getattr(ins_ver, "data", None):
            raise HTTPException(status_code=500, detail="DB no devolvió datos al insertar versión")

        # Respuesta
        return {**doc_payload, "date_ref": date_ref}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo creando documento: {e}")

@app.get("/documents", response_model=DocumentListOut)
def list_documents(
    q: Optional[str] = Query(None, description="Búsqueda por título (ilike)"),
    category_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    ensure_supabase()
    """
    Lista documentos con filtros simples.
    """
    query = sb.table("documents").select("*", count="exact").order("created_at", desc=True)

    if q:
        query = query.ilike("title", f"%{q}%")
    if category_id is not None:
        query = query.eq("category_id", category_id)
    if date_from:
        query = query.gte("date_ref", str(date_from))
    if date_to:
        query = query.lte("date_ref", str(date_to))

    res = query.range(offset, offset + limit - 1).execute()
    rows = getattr(res, "data", []) or []
    total = getattr(res, "count", None)
    if total is None:
        total = len(rows)
    return {"items": rows, "total": total}

@app.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str):
    ensure_supabase()
    res = sb.table("documents").select("*").eq("id", doc_id).single().execute()
    data = getattr(res, "data", None)
    if not data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return data

@app.get("/documents/{doc_id}/versions")
def list_versions(doc_id: str):
    ensure_supabase()
    res = sb.table("document_versions").select("*").eq("document_id", doc_id).order("version", desc=True).execute()
    return getattr(res, "data", []) or []

@app.post("/documents/{doc_id}/versions")
async def add_version(
    doc_id: str,
    note: Optional[str] = Form(None),
    file: UploadFile = File(...),
):
    ensure_supabase()
    # Traer doc
    doc_res = sb.table("documents").select("*").eq("id", doc_id).single().execute()
    doc = getattr(doc_res, "data", None)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    curr = int(doc["current_version"])
    new_v = curr + 1

    filename = safe_filename(file.filename or f"v{new_v}")
    storage_path = f"{doc_id}/v{new_v}/{filename}"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    checksum = sha256_bytes(content)
    mime_type = file.content_type or "application/octet-stream"

    up_res = sb.storage.from_(BUCKET).upload(
        path=storage_path,
        file=content,
        file_options={"content-type": mime_type, "x-upsert": "false"},
    )
    if isinstance(up_res, dict) and up_res.get("error"):
        raise HTTPException(status_code=500, detail=f"Error subiendo a Storage: {up_res['error']}")

    ins_ver = sb.table("document_versions").insert({
        "document_id": doc_id,
        "version": new_v,
        "storage_path": storage_path,
        "checksum": checksum,
        "size_bytes": len(content),
        "mime_type": mime_type,
        "note": note,
    }).execute()
    if not getattr(ins_ver, "data", None):
        raise HTTPException(status_code=500, detail="DB no devolvió datos al insertar versión")

    up_doc = sb.table("documents").update({"current_version": new_v}).eq("id", doc_id).execute()
    if not getattr(up_doc, "data", None):
        raise HTTPException(status_code=500, detail="DB no devolvió datos al actualizar documento")

    return {"ok": True, "version": new_v}

@app.get("/documents/{doc_id}/download")
def download_signed_url(doc_id: str, version: Optional[int] = None, expire_seconds: int = 3600):
    """
    Devuelve un link firmado temporal para descargar (no público).
    """
    ensure_supabase()
    q = sb.table("document_versions").select("storage_path,version").eq("document_id", doc_id)
    if version is not None:
        q = q.eq("version", version)
    res = q.order("version", desc=True).limit(1).execute()
    rows = getattr(res, "data", []) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Versión no encontrada")

    storage_path = rows[0]["storage_path"]
    signed = sb.storage.from_(BUCKET).create_signed_url(storage_path, expire_seconds)
    if not signed or "signed_url" not in signed:
        raise HTTPException(status_code=500, detail=f"No se pudo firmar URL: {signed}")

    return {"url": signed["signed_url"], "expires_in": expire_seconds}
@app.get("/")
def root():
    return {"ok": True, "service": "Digitalizacion Fabrica API"}
