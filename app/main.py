from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID
import hashlib, json, re, uuid

from supabase import create_client, Client
from app.config import settings

app = FastAPI(title="Digitalizacion Fabrica - API (Simulacro)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOW_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE:
    raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE")

sb: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE)

SAFE_CHARS = re.compile(r"[^a-zA-Z0-9._-]+")

def safe_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return SAFE_CHARS.sub("_", name)

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

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
    try:
        tags_list = [t.strip() for t in tags.split(",")] if tags else []
        extra_dict = json.loads(extra) if extra else {}

        doc_id = str(uuid.uuid4())
        version = 1
        filename = safe_filename(file.filename or "archivo")
        storage_path = f"{doc_id}/v{version}/{filename}"

        content = await file.read()
        checksum = sha256_bytes(content)
        mime_type = file.content_type or "application/octet-stream"

        up_res = sb.storage.from_("traza-docs").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": mime_type, "x-upsert": "false"},
        )
        # Si el SDK devuelve error, normalmente viene en 'error' o status_code
        if hasattr(up_res, "status_code") and up_res.status_code >= 400:
            raise HTTPException(status_code=500, detail=f"Error subiendo a Storage: {up_res}")
        if isinstance(up_res, dict) and up_res.get("error"):
            raise HTTPException(status_code=500, detail=f"Error subiendo a Storage: {up_res['error']}")

        doc_payload = {
            "id": doc_id,
            "title": title,
            "category_id": category_id,
            "status": "vigente",
            "current_version": version,
            "date_ref": str(date_ref) if date_ref else None,
            "tags": tags_list,
            "extra": extra_dict,
            "created_by": None,
        }
        ins_doc = sb.table("documents").insert(doc_payload).execute()
        if ins_doc.error:
            sb.storage.from_("traza-docs").remove([storage_path])
            raise HTTPException(status_code=500, detail=f"Error insertando documento: {ins_doc.error}")

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
        if ins_ver.error:
            raise HTTPException(status_code=500, detail=f"Error insertando versión: {ins_ver.error}")

        return {**doc_payload, "date_ref": date_ref}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo creando documento: {e}")

@app.get("/documents", response_model=DocumentListOut)
def list_documents(
    q: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
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
    if res.error:
        raise HTTPException(status_code=500, detail=str(res.error))
    rows = res.data or []
    total = res.count or len(rows)
    return {"items": rows, "total": total}

@app.get("/documents/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str):
    doc = sb.table("documents").select("*").eq("id", doc_id).single().execute()
    if doc.error or not doc.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    return doc.data

@app.get("/documents/{doc_id}/versions")
def list_versions(doc_id: str):
    res = sb.table("document_versions").select("*").eq("document_id", doc_id).order("version", desc=True).execute()
    if res.error:
        raise HTTPException(status_code=500, detail=str(res.error))
    return res.data

@app.post("/documents/{doc_id}/versions")
async def add_version(doc_id: str, note: Optional[str] = Form(None), file: UploadFile = File(...)):
    doc = sb.table("documents").select("*").eq("id", doc_id).single().execute()
    if doc.error or not doc.data:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    curr = int(doc.data["current_version"])
    new_v = curr + 1

    filename = safe_filename(file.filename or f"v{new_v}")
    storage_path = f"{doc_id}/v{new_v}/{filename}"
    content = await file.read()
    checksum = sha256_bytes(content)
    mime_type = file.content_type or "application/octet-stream"

    up_res = sb.storage.from_("traza-docs").upload(
        path=storage_path,
        file=content,
        file_options={"content-type": mime_type, "x-upsert": "false"},
    )
    if hasattr(up_res, "status_code") and up_res.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"Error subiendo a Storage: {up_res}")
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
    if ins_ver.error:
        raise HTTPException(status_code=500, detail=f"Error insertando versión: {ins_ver.error}")

    up_doc = sb.table("documents").update({"current_version": new_v}).eq("id", doc_id).execute()
    if up_doc.error:
        raise HTTPException(status_code=500, detail=f"Error actualizando documento: {up_doc.error}")

    return {"ok": True, "version": new_v}

@app.get("/documents/{doc_id}/download")
def download_signed_url(doc_id: str, version: Optional[int] = None, expire_seconds: int = 3600):
    q = sb.table("document_versions").select("storage_path,version").eq("document_id", doc_id)
    if version is not None:
        q = q.eq("version", version)
    res = q.order("version", desc=True).limit(1).execute()
    if res.error or not res.data:
        raise HTTPException(status_code=404, detail="Versión no encontrada")

    storage_path = res.data[0]["storage_path"]
    signed = sb.storage.from_("traza-docs").create_signed_url(storage_path, expire_seconds)
    if not signed or "signed_url" not in signed:
        raise HTTPException(status_code=500, detail=f"No se pudo firmar URL: {signed}")

    return {"url": signed["signed_url"], "expires_in": expire_seconds}
