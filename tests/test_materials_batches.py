import os
from datetime import date

# Ensure env vars before importing app
os.environ.setdefault("SUPABASE_ENABLED", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

import pytest


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_materials_batches_flow():
    # Crear material
    resp = client.post("/materials/", json={"name": "Steel", "description": "A"})
    assert resp.status_code == 201
    mat = resp.json()
    mat_id = mat["id"]

    # Crear batch
    payload = {
        "material_id": mat_id,
        "batch_code": "B001",
        "quantity": 5,
        "production_date": "2024-01-01",
    }
    resp = client.post("/batches/", json=payload)
    assert resp.status_code == 201
    batch = resp.json()

    # Listar por material_id
    resp = client.get(f"/batches/?material_id={mat_id}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1

    # Duplicados
    resp = client.post("/materials/", json={"name": "Steel"})
    assert resp.status_code == 409

    resp = client.post("/batches/", json=payload)
    assert resp.status_code == 409

    # Soft delete batch
    resp = client.delete(f"/batches/{batch['id']}")
    assert resp.status_code == 204
    resp = client.get(f"/batches/?material_id={mat_id}")
    assert resp.status_code == 200
    assert resp.json() == []

    # Soft delete material
    resp = client.delete(f"/materials/{mat_id}")
    assert resp.status_code == 204
    resp = client.get("/materials/")
    assert resp.status_code == 200
    assert resp.json() == []
