import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_and_filter_batch(client):
    # Create material
    res = client.post("/materials", json={"name": "Steel"})
    assert res.status_code == 201
    material_id = res.json()["id"]

    # Create batch
    res = client.post(
        "/batches",
        json={
            "material_id": material_id,
            "batch_code": "B1",
            "quantity": 5,
            "production_date": "2024-01-01",
        },
    )
    assert res.status_code == 201

    # List batches filtered by material_id
    res = client.get(f"/batches?material_id={material_id}")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["batch_code"] == "B1"


def test_duplicates(client):
    res = client.post("/materials", json={"name": "Iron"})
    assert res.status_code == 201
    material_id = res.json()["id"]

    # Duplicate material
    res = client.post("/materials", json={"name": "Iron"})
    assert res.status_code == 409

    # Batch unique per (material_id, batch_code)
    res = client.post(
        "/batches",
        json={
            "material_id": material_id,
            "batch_code": "X1",
            "quantity": 1,
            "production_date": "2024-01-02",
        },
    )
    assert res.status_code == 201

    res = client.post(
        "/batches",
        json={
            "material_id": material_id,
            "batch_code": "X1",
            "quantity": 2,
            "production_date": "2024-01-03",
        },
    )
    assert res.status_code == 409


def test_soft_delete(client):
    # Material
    res = client.post("/materials", json={"name": "Copper"})
    material_id = res.json()["id"]
    del_res = client.delete(f"/materials/{material_id}")
    assert del_res.status_code == 204
    res = client.get("/materials")
    ids = [m["id"] for m in res.json()]
    assert material_id not in ids

    # Batch
    res_mat = client.post("/materials", json={"name": "Aluminium"})
    mat_id = res_mat.json()["id"]
    res_batch = client.post(
        "/batches",
        json={
            "material_id": mat_id,
            "batch_code": "B-1",
            "quantity": 3,
            "production_date": "2024-01-04",
        },
    )
    batch_id = res_batch.json()["id"]
    del_res = client.delete(f"/batches/{batch_id}")
    assert del_res.status_code == 204
    res = client.get(f"/batches?material_id={mat_id}")
    assert res.json() == []
