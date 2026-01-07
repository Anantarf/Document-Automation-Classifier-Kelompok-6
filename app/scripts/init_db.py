
# scripts/init_db.py
"""
Membuat folder storage dan inisialisasi database SQLite.
"""
import os
from app.config import settings
from app.database import engine, Base

# Buat folder untuk DB & storage
os.makedirs(os.path.dirname(settings.sqlite_db_path), exist_ok=True)
os.makedirs(settings.storage_root, exist_ok=True)
os.makedirs(settings.temp_upload_dir, exist_ok=True)

# Buat tabel
Base.metadata.create_all(bind=engine)

print('DB & folder siap:')
print('  DB Path      :', settings.sqlite_db_path)
print('  Storage Root :', settings.storage_root)
print('  Temp Upload  :', settings.temp_upload_dir)
