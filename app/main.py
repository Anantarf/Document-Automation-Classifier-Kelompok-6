
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

# `Base` is defined centrally in `app.models` to avoid duplicate declarations.
from contextlib import asynccontextmanager
import logging

# 1) Muat .env PALING AWAL agar os.getenv terbaca di config
try:
    from dotenv import load_dotenv
    load_dotenv()  # aman dipanggil berkali-kali (idempotent)
except Exception:
    # dotenv opsional; kalau tidak ada tetap lanjut
    pass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# 2) Import config & database (settings sekarang ada di config.py)
from app.config import settings, ensure_dirs
from app.database import init_db

# 3) Import routers (pastikan nama modul sesuai)
#    Jika nama file berbeda, sesuaikan import di bawah ini.
from app.routers import upload, search, export, health, auth

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
        
        # Seed Admin
        from app.database import SessionLocal
        from app.routers.auth import create_initial_admin
        db = SessionLocal()
        try:
            create_initial_admin(db)
        finally:
            db.close()
            
        log.info(
            "[startup] DB: %s | STORAGE: %s | UPLOADS: %s",
            settings.DB_FILE,
            settings.STORAGE_ROOT_DIR,
            settings.TEMP_UPLOAD_PATH,
        )
    except Exception as e:
        # Logging jelas agar mudah debug saat spawn-reload di Windows
        log.error("Startup failed: %s", e, exc_info=True)
        # Biarkan raise agar server tidak jalan dalam kondisi rusak
        raise

    yield

    # SHUTDOWN: tempat menutup resource jika perlu
    log.info("[shutdown] Document Automation Classifier stopped.")


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

# ----- CORS (secure by default; sesuaikan untuk produksi) -----
# DEVELOPMENT: lokal frontend bisa akses
# PRODUCTION: restrict ke domain spesifik saja!
cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",  # Vite dev server default
    "http://127.0.0.1:5173",
    "http://localhost:5174",  # Vite alternate port
    "http://127.0.0.1:5174",
]

# Allow CORS origins dari env variable jika ada
import os
env_origins = os.getenv("CORS_ORIGINS", "").split(",")
cors_origins.extend([o.strip() for o in env_origins if o.strip()])

# TEMPORARY DEBUG: allow all origins in development
if os.getenv("APP_ENV", "").lower() == "development":
    log.warning("⚠️  CORS: Allowing ALL origins (development mode)")
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Restrict methods untuk security
    allow_headers=["*"],
)

# ----- Rate Limiting (slowapi) -----
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"detail": "Too many requests. Please try again later."},
))

# ----- Security Headers Middleware -----
# TEMPORARILY DISABLED FOR DEBUGGING
# @app.middleware("http")
# async def add_security_headers(request: Request, call_next):
#     response = await call_next(request)
#     
#     # HSTS: Force HTTPS (1 year)
#     # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
#     
#     # Prevent clickjacking
#     # response.headers["X-Frame-Options"] = "DENY"
#     
#     # Prevent MIME type sniffing
#     # response.headers["X-Content-Type-Options"] = "nosniff"
#     
#     # XSS Protection
#     # response.headers["X-XSS-Protection"] = "1; mode=block"
#     
#     # Content Security Policy
#     # response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
#     
#     # Referrer Policy
#     # response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
#     
#     # Permissions Policy
#     # response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
#     
#     # Remove server info (don't expose FastAPI/Python version)
#     # response.headers.pop("server", None)
#     
#     return response

# ----- Trusted Host Middleware -----
# Uncomment for production, specify allowed hosts
# app.add_middleware(
#     TrustedHostMiddleware,
#     allowed_hosts=["yourdomain.com", "www.yourdomain.com"],
# )

# ----- Root & Health -----
@app.get("/", tags=["Root"])
def root():
    return {"app": "Document Automation Classifier", "status": "ok"}

@app.get("/healthz", tags=["Root"])
@limiter.limit("100/minute")
def healthz(request: Request):
    # Bisa ditambah cek sederhana (misal file DB ada, storage dapat ditulis, dsb.)
    return {"status": "healthy"}

# ----- Include Routers -----
# Jika di masing-masing router sudah ada prefix (misal @router.post("/upload")), cukup include saja.
# Jika kamu ingin prefix global seperti "/api", pakai: app.include_router(upload.router, prefix="/api")
app.include_router(upload.router, tags=["Upload"])
app.include_router(search.router, tags=["Search"])
app.include_router(export.router, tags=["Export"])
# Health endpoints (OCR check, etc.)
# Health endpoints (OCR check, etc.)
app.include_router(health.router)
app.include_router(auth.router)

# Document endpoints (metadata, file, text)
try:
    from app.routers import documents
    app.include_router(documents.router, tags=["Documents"])
except Exception:
    log.warning("Documents router not available")

# ----- Catatan untuk menjalankan uvicorn -----
# python -m uvicorn app.main:app --reload
# Di Windows, --reload menggunakan spawn process → startup dipanggil ulang saat file berubah (normal).
