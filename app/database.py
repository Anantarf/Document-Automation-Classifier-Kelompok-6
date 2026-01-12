
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.config import DB_FILE, ensure_dirs

ensure_dirs()

def _sqlite_url_from_path(p: Path) -> str:
    return f"sqlite:///{p.as_posix()}"

SQLALCHEMY_DATABASE_URL = _sqlite_url_from_path(DB_FILE)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    # LAZY IMPORT -> hindari circular import
    from app.models import Base
    Base.metadata.create_all(bind=engine)
