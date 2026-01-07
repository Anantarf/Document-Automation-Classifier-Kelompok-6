
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.config import DB_FILE, ensure_dirs

# Pastikan folder dibuat sebelum engine terbentuk
ensure_dirs()

def _sqlite_url_from_path(p: Path) -> str:
    """
    Build URL SQLite yang valid untuk SQLAlchemy.
    Gunakan forward slashes (Path.as_posix) agar aman untuk spasi/backslash Windows.
    Contoh: sqlite:///C:/Users/.../data/app.db
    """
    return f"sqlite:///{p.as_posix()}"

SQLALCHEMY_DATABASE_URL = _sqlite_url_from_path(DB_FILE)

# Thread-safety untuk FastAPI (background/task lintas thread)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Buat tabel-tabel jika belum ada (idempotent).
    Import Base dilakukan di dalam fungsi untuk menghindari circular import.
    """
    from app.models import Base
    Base.metadata.create_all(bind=engine)
