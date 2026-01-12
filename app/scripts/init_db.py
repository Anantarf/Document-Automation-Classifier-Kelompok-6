
# scripts/init_db.py
"""
Membuat folder storage dan inisialisasi database SQLite.
"""
import os
from app.config import settings
from app.database import engine
from app.models import Base

# Gunakan helper ensure_dirs() agar konsisten dengan konfigurasi
settings.ensure_dirs()

# Buat tabel jika belum ada
Base.metadata.create_all(bind=engine)

print('DB & folder siap:')
print('  DB Path      :', settings.DB_FILE)
print('  Storage Root :', settings.STORAGE_ROOT_DIR)
print('  Temp Upload  :', settings.TEMP_UPLOAD_PATH)
