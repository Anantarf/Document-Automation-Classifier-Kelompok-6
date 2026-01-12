"""
scripts/update_metadata_from_ocr.py

For every document in DB, re-run text extraction (OCR) on the stored file and update metadata.json and DB
if parsed results differ (especially year). Moves files to new year folder when needed (with backup).
"""
from pathlib import Path
import shutil
import json
import re
from datetime import datetime

from app.database import SessionLocal
from app.models import Document
from app.services.text_extraction import extract_text_and_save
from app.services.metadata import parse_metadata
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

    orig_path = Path(doc.stored_path)
    if not orig_path.exists():
        print("  original file not found, skipping")
        return False

    content = orig_path.read_bytes()
    temp_base = Path('storage/tmp_ocr')
    temp_base.mkdir(parents=True, exist_ok=True)
    text_path, text_content, ocr_used = extract_text_and_save(content=content, mime_type=doc.mime_type, base_dir=temp_base)

    parsed = parse_metadata(text_content or '', orig_path.name, uploaded_at=doc.uploaded_at or datetime.utcnow())
    parsed_tahun = parsed.get('tahun')
    try:
        parsed_tahun = int(parsed_tahun) if parsed_tahun is not None else None
    except Exception:
        parsed_tahun = None

    # Load existing metadata
    md = json.loads(meta_path.read_text(encoding='utf-8'))

    changed = False
    # update parsed fields in metadata
    md['parsed'] = parsed
    if ocr_used:
        from app.constants import TEXT_FILENAME
        md['ocr_enabled'] = True
        # save text file in the base dir
        tpath = base_dir / TEXT_FILENAME
        tpath.write_text(text_content or '', encoding='utf-8')
        md['text_path'] = tpath.as_posix()
        changed = True

    # if parsed fields better than existing ones, update them
    if parsed.get('nomor') and (not md.get('nomor') or md.get('nomor') in ['', 'string', 'TANPA-NOMOR']):
        md['nomor'] = parsed.get('nomor')
        changed = True
    if parsed.get('perihal') and (not md.get('perihal') or md.get('perihal') in ['', 'string']):
        md['perihal'] = parsed.get('perihal')
        changed = True

    # if year differs and parsed_tahun valid, move directory
    if parsed_tahun and parsed_tahun > 0 and parsed_tahun != md.get('tahun'):
        new_slug = slugify_nomor(md.get('nomor') or parsed.get('nomor'))
        new_base = settings.STORAGE_ROOT_DIR / str(parsed_tahun) / (doc.jenis or 'keluar') / new_slug
        backup = backup_folder(base_dir)
        if backup:
            print(f"  backup created at {backup}")
        new_base.parent.mkdir(parents=True, exist_ok=True)
        for p in base_dir.iterdir():
            shutil.move(str(p), str(new_base / p.name))
        # Update md paths
        from app.constants import METADATA_FILENAME
        md['tahun'] = parsed_tahun
        md['file_original'] = (new_base / Path(doc.stored_path).name).name
        md_path_new = new_base / METADATA_FILENAME
        md_path_new.write_text(json.dumps(md, ensure_ascii=False, indent=2), encoding='utf-8')
        # Update DB fields
        doc.tahun = parsed_tahun
        doc.stored_path = str(new_base / Path(doc.stored_path).name)
        doc.metadata_path = str(md_path_new)
        doc.nomor_surat = md.get('nomor') or doc.nomor_surat
        doc.perihal = md.get('perihal') or doc.perihal
        print(f"  moved to {new_base}")
        changed = True
    else:
        # write metadata back in-place if changed
        if changed:
            meta_path.write_text(json.dumps(md, ensure_ascii=False, indent=2), encoding='utf-8')

    return changed


def main():
    db = SessionLocal()
    try:
        rows = db.query(Document).all()
        print(f"Found {len(rows)} documents to check")
        updated = 0
        for r in rows:
            ok = process_one(r)
            if ok:
                db.add(r)
                db.commit()
                updated += 1
                print(f"  updated doc id={r.id}")
        print(f"Done. Updated {updated} documents.")
    finally:
        db.close()

if __name__ == '__main__':
    main()
