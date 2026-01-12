"""
scripts/fix_year_zero.py

Scan database for records with tahun==0 (or missing), attempt to read their metadata.json and parsed.tahun,
then move files to the correct year folder and update metadata.json and DB accordingly.

It will backup original folder before moving.

Usage:
  .\.venv\Scripts\Activate.ps1
  python scripts/fix_year_zero.py

This script prints summary and performs changes in-place (with backups).
"""
from pathlib import Path
import shutil
import json
import re
from datetime import datetime

from app.database import SessionLocal
from app.models import Document
from app.config import settings
from app.utils.slugs import slugify_nomor
from app.utils.fileops import backup_folder


def process_one(doc: Document):
    meta_path = Path(doc.metadata_path)
    base_dir = meta_path.parent
    print(f"Processing doc id={doc.id} base={base_dir}")
    if not meta_path.exists():
        print("  metadata.json not found, skipping")
        return False
    md = json.loads(meta_path.read_text(encoding='utf-8'))
    parsed = md.get('parsed', {})
    tahun = parsed.get('tahun')
    if not tahun:
        print("  parsed.tahun missing, skipping")
        return False
    try:
        tahun = int(tahun)
    except Exception:
        print("  parsed.tahun not an int, skipping")
        return False

    nomor = parsed.get('nomor') or md.get('nomor') or doc.nomor_surat or ''
    slug = slugify_nomor(nomor)
    new_base = settings.STORAGE_ROOT_DIR / str(tahun) / (doc.jenis or 'keluar') / slug

    # Backup
    bkp = backup_folder(base_dir)
    if bkp:
        print(f"  backup created at {bkp}")

    new_base.parent.mkdir(parents=True, exist_ok=True)
    # Move contents
    for p in base_dir.iterdir():
        shutil.move(str(p), str(new_base / p.name))

    # Update metadata
    md['tahun'] = tahun
    md['file_original'] = (new_base / Path(doc.stored_path).name).name
    md['text_path'] = md.get('text_path')  # keep as-is (may be None)
    md['ocr_enabled'] = md.get('ocr_enabled', False)

    from app.constants import METADATA_FILENAME
    new_meta_path = new_base / METADATA_FILENAME
    new_meta_path.write_text(json.dumps(md, ensure_ascii=False, indent=2), encoding='utf-8')

    # Update DB
    doc.tahun = tahun
    doc.nomor_surat = md.get('nomor') or doc.nomor_surat
    doc.perihal = md.get('perihal') or doc.perihal
    # stored_path: find original file in new_base (original.pdf or original.docx)
    orig_candidates = [p for p in new_base.iterdir() if p.name.startswith('original.')]
    if orig_candidates:
        doc.stored_path = str(orig_candidates[0])
    doc.metadata_path = str(new_meta_path)

    return True


def main():
    db = SessionLocal()
    try:
        rows = db.query(Document).filter(Document.tahun == 0).all()
        print(f"Found {len(rows)} documents with tahun==0")
        changed = 0
        for r in rows:
            ok = process_one(r)
            if ok:
                db.add(r)
                db.commit()
                changed += 1
                print(f"  updated doc id={r.id}")
        print(f"Done. Updated {changed} documents.")
    finally:
        db.close()

if __name__ == '__main__':
    main()
