import os
from fastapi.testclient import TestClient

# Forzar SQLite en sandbox y desactivar supabase
os.environ.setdefault("DATABASE_URL", "sqlite:///./dev.db")
os.environ.setdefault("SUPABASE_ENABLED", "false")

from app.main import app


def test_db_fallback_creates_tables_and_post_material_works():
    # empezar con DB limpia
    try:
        os.remove("dev.db")
    except FileNotFoundError:
        pass

    # usar TestClient para disparar eventos de startup
    with TestClient(app) as client:
        r = client.post("/materials", json={"name": "Envase PET 500", "description": "botella 500 ml"})
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert "id" in data and data["name"] == "Envase PET 500"
