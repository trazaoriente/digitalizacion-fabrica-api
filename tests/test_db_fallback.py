import os
import importlib
from fastapi.testclient import TestClient

# Forzar SQLite en sandbox, desactivar supabase y migraciones
os.environ.setdefault("DATABASE_URL", "sqlite:///./dev.db")
os.environ.setdefault("SUPABASE_ENABLED", "false")
os.environ.setdefault("RUN_MIGRATIONS", "false")


def test_db_fallback_creates_tables_and_post_material_works():
    # empezar con DB limpia antes de importar la app
    try:
        os.remove("dev.db")
    except FileNotFoundError:
        pass

    # Recargar módulos para tomar las nuevas variables
    import app.database as database
    import app.models as models
    import app.main as main

    importlib.reload(database)
    importlib.reload(models)
    importlib.reload(main)

    app = main.app

    # usar TestClient para disparar eventos de startup
    with TestClient(app) as client:
        r = client.post(
            "/materials",
            json={"name": "Envase PET 500", "description": "botella 500 ml"},
        )
        assert r.status_code in (200, 201), r.text
        data = r.json()
        assert "id" in data and data["name"] == "Envase PET 500"
