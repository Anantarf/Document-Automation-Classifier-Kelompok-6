
# app/main.py
"""
Document Automation Classifier - FastAPI main entry.

Fitur:
- Lifespan startup: load .env, ensure dirs, init DB.
- CORS untuk dev.
- Root/health endpoint.
- Include routers: upload, search, export.

Struktur proyek (ringkas):
app/
  ├─ main.py
  ├─ config.py
  ├─ database.py
  ├─ models.py
  ├─ schemas.py
  ├─ routers/
  │    ├─ upload.py
  │    ├─ search.py
  │    └─ export.py
  ├─ services/
  └─ utils/
.env
data/
storage/
"""

from sqlalchemy.orm import declarative_base
Base = declarative_base()

from contextlib import asynccontextmanager
import logging

# 1) Muat .env PALING AWAL agar os.getenv terbaca di config
try:
    from dotenv import load_dotenv
    load_dotenv()  # aman dipanggil berkali-kali (idempotent)
except Exception:
    # dotenv opsional; kalau tidak ada tetap lanjut
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 2) Import config & database (settings sekarang ada di config.py)
from app.config import settings, ensure_dirs
from app.database import init_db

# 3) Import routers (pastikan nama modul sesuai)
#    Jika nama file berbeda, sesuaikan import di bawah ini.
from app.routers import upload, search, export

# ----- Logging (gunakan logger uvicorn agar nyatu di console) -----
log = logging.getLogger("uvicorn")

# ----- Tags metadata utk Swagger UI (opsional) -----
tags_metadata = [
    {
        "name": "Root",
        "description": "Status aplikasi & health check.",
    },
    {
        "name": "Upload",
        "description": "Unggah DOCX/PDF (OCR untuk PDF scan), simpan metadata & foldering.",
    },
    {
        "name": "Search",
        "description": "Pencarian/filter berdasarkan tahun/jenis/nomor/perihal.",
    },
    {
        "name": "Export",
        "description": "Ekspor hasil pencarian dalam format ZIP/CSV.",
    },
]

# ----- Lifespan (startup/shutdown) -----
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP: pastikan folder ada dulu, baru init DB
    try:
        ensure_dirs()
        init_db()
        log.info(
            "[startup] DB: %s | STORAGE: %s | UPLOADS: %s",
            settings.DB_FILE,
            settings.STORAGE_ROOT_DIR,
            settings.TEMP_UPLOAD_DIR_DIR,
        )
    except Exception as e:
        # Logging jelas agar mudah debug saat spawn-reload di Windows
        log.error("Startup failed: %s", e, exc_info=True)
        # Biarkan raise agar server tidak jalan dalam kondisi rusak
        raise

    yield

    # SHUTDOWN: tempat menutup resource jika perlu
    log.info("[shutdown] Document Automation Classifier stopped.")

# ----- Buat app FastAPI -----
app = FastAPI(
    title="Document Automation Classifier",
    description=(
        "Automasi klasifikasi surat (masuk/keluar) dengan penyimpanan terstruktur per tahun, "
        "metadata JSON, pencarian, dan ekspor ZIP/CSV. Format upload: DOCX & PDF (OCR untuk PDF scan)."
    ),
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# ----- CORS (dev; sesuaikan origin untuk produksi) -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ganti ke ["http://localhost:3000", "http://127.0.0.1:3000"] jika perlu
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Root & Health -----
@app.get("/", tags=["Root"])
def root():
    return {"app": "Document Automation Classifier", "status": "ok"}

@app.get("/healthz", tags=["Root"])
def healthz():
    # Bisa ditambah cek sederhana (misal file DB ada, storage dapat ditulis, dsb.)
    return {"status": "healthy"}

# ----- Include Routers -----
# Jika di masing-masing router sudah ada prefix (misal @router.post("/upload")), cukup include saja.
# Jika kamu ingin prefix global seperti "/api", pakai: app.include_router(upload.router, prefix="/api")
app.include_router(upload.router, tags=["Upload"])
app.include_router(search.router, tags=["Search"])
app.include_router(export.router, tags=["Export"])

# ----- Catatan untuk menjalankan uvicorn -----
# python -m uvicorn app.main:app --reload
# Di Windows, --reload menggunakan spawn process → startup dipanggil ulang saat file berubah (normal).
