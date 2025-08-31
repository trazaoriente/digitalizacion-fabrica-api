import os
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./dev.db")
os.environ.setdefault("SUPABASE_ENABLED", "false")
os.environ.setdefault("RUN_MIGRATIONS", "false")

from app.main import app


def test_startup_and_post_material_on_fresh_sqlite():
    try:
        os.remove("dev.db")
    except FileNotFoundError:
        pass

    with TestClient(app) as client:
        r = client.post("/materials", json={"name":"Envase PET 500","description":"botella 500 ml"})
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert data["name"] == "Envase PET 500"
