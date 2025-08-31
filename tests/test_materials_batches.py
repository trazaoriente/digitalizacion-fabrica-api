import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

# Configurar base de datos en memoria antes de importar la app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app  # noqa: E402
from app.database import Base, engine  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_material_and_batch(client):
    res = client.post("/materials", json={"name": "Acero"})
    assert res.status_code == 201
    mat_id = res.json()["id"]

    batch_payload = {
        "material_id": mat_id,
        "batch_code": "L001",
        "quantity": 10,
        "production_date": "2024-01-01",
    }
    res = client.post("/batches", json=batch_payload)
    assert res.status_code == 201

    res = client.get(f"/batches?material_id={mat_id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["batch_code"] == "L001"


def test_duplicate_material_name(client):
    client.post("/materials", json={"name": "M1"})
    res = client.post("/materials", json={"name": "M1"})
    assert res.status_code == 409


def test_duplicate_batch(client):
    res = client.post("/materials", json={"name": "Mat"})
    mat_id = res.json()["id"]
    payload = {
        "material_id": mat_id,
        "batch_code": "B1",
        "quantity": 5,
        "production_date": "2024-01-01",
    }
    res = client.post("/batches", json=payload)
    assert res.status_code == 201
    res = client.post("/batches", json=payload)
    assert res.status_code == 409
