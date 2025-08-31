import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Try to run migrations; if it fails, create tables directly
try:
    from alembic import command
    from alembic.config import Config
    import pathlib

    BASE_DIR = pathlib.Path(__file__).resolve().parent
    alembic_cfg = Config(str(BASE_DIR.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
except Exception:
    Base.metadata.create_all(bind=engine)
