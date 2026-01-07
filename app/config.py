
# app/config.py
import os
from pathlib import Path
from typing import Optional

# Base project dir = .../BISMILAH P3L BERES
BASE_DIR = Path(__file__).resolve().parent.parent

def _env(key: str, default: Optional[str] = None) -> str:
    val = os.getenv(key)
    return val if val is not None else (default or "")

def as_abs_path(path_like: str) -> Path:
    """
    Konversi path env menjadi absolute Path yang aman di Windows/Linux.
    - Jika env berisi absolute Windows (C:\...), tetap dipakai.
    - Jika relatif (data/app.db), gabungkan ke BASE_DIR.
    """
    p = Path(path_like)
    if not p.is_absolute():
        p = (BASE_DIR / path_like)
    return p.resolve()

class Settings:
    """
    Objek settings kompatibel dengan impor lama: from app.config import settings
    Membaca .env via os.getenv (pastikan load_dotenv dipanggil di main.py).
    """
    def __init__(self) -> None:
        self.SQLITE_DB_PATH = _env("SQLITE_DB_PATH", "data/app.db")
        self.STORAGE_ROOT = _env("STORAGE_ROOT", "storage/arsip_kelurahan")
        self.TEMP_UPLOAD_DIR = _env("TEMP_UPLOAD_DIR", "storage/uploads")
        self.TESSERACT_CMD = _env("TESSERACT_CMD", "")

        # absolute variants (Path)
        self.DB_FILE = as_abs_path(self.SQLITE_DB_PATH)
        self.STORAGE_ROOT_DIR = as_abs_path(self.STORAGE_ROOT)
        self.TEMP_UPLOAD_DIR_DIR = as_abs_path(self.TEMP_UPLOAD_DIR)

    def ensure_dirs(self) -> None:
        """
        Buat folder-folder penting jika belum ada.
        Penting: SQLite hanya bisa create FILE, bukan FOLDER.
        """
        self.DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.STORAGE_ROOT_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_UPLOAD_DIR_DIR.mkdir(parents=True, exist_ok=True)

# Ekspor objek settings untuk kompatibilitas impor lama
settings = Settings()

# Alias untuk kompatibilitas patch lain
DB_FILE = settings.DB_FILE
STORAGE_ROOT_DIR = settings.STORAGE_ROOT_DIR
TEMP_UPLOAD_DIR_DIR = settings.TEMP_UPLOAD_DIR_DIR

def ensure_dirs():
    settings.ensure_dirs()
