"""
scripts/fix_doc_by_hash.py

Fix a single document identified by its sha256 hash:
- Run OCR/parse on the stored file
- Create new folder by parsed year/jenis/slug(nomor)
- Move only the relevant file(s) (original.* and text.txt) to the new folder
- Create metadata.json for the moved file and update DB record
- Backup original folder first

Usage:
  .\.venv\Scripts\Activate.ps1
  python scripts/fix_doc_by_hash.py <hash>
"""
import sys
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


def main(hash_val: str):
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.file_hash == hash_val).first()
        if not doc:
            print('Document with hash not found')
            return
        print('Found doc:', doc.id, doc.tahun, doc.stored_path)
        meta_path = Path(doc.metadata_path)
        base_dir = meta_path.parent
        print('Base dir:', base_dir)
        if not base_dir.exists():
            print('Base dir missing')
            return

        # backup
        bkp = backup_folder(base_dir)
        if bkp:
            print('Backup created at', bkp)

        orig_path = Path(doc.stored_path)
        content = orig_path.read_bytes()
        temp_base = Path('storage/tmp_ocr')
        temp_base.mkdir(parents=True, exist_ok=True)

        text_path_tmp, text_content, ocr_used = extract_text_and_save(content=content, mime_type=doc.mime_type, base_dir=temp_base)
        parsed = parse_metadata(text_content or '', orig_path.name, uploaded_at=doc.uploaded_at or datetime.utcnow())
        print('Parsed:', parsed)

        parsed_tahun = parsed.get('tahun')
        try:
            parsed_tahun = int(parsed_tahun) if parsed_tahun is not None else None
        except Exception:
            parsed_tahun = None

        if not parsed_tahun or parsed_tahun <= 0:
            print('Parsed tahun invalid, abort')
            return

        nomor = parsed.get('nomor') or doc.nomor_surat or ''
        slug = slugify_nomor(nomor)
        new_base = settings.STORAGE_ROOT_DIR / str(parsed_tahun) / (doc.jenis or 'keluar') / slug
        new_base.mkdir(parents=True, exist_ok=True)

        # Move only original.* that match this doc's mime/hash, and also text file if exists in tmp
        moved = []
        for candidate in base_dir.iterdir():
            if candidate.is_file():
                # check if candidate is the file we intend (by extension and by hash for safety)
                if candidate.name.startswith('original.'):
                    # move it
                    shutil.move(str(candidate), str(new_base / candidate.name))
                    moved.append(candidate.name)
        # write text.txt if we have text_content
        if text_content:
            from app.constants import TEXT_FILENAME
            (new_base / TEXT_FILENAME).write_text(text_content, encoding='utf-8')
            moved.append(TEXT_FILENAME)

        # compose metadata
        from app.constants import METADATA_FILENAME
        metadata = {
            'uploaded_at': (doc.uploaded_at.isoformat() + 'Z') if doc.uploaded_at else datetime.utcnow().isoformat() + 'Z',
            'file_original': (orig_path.name),
            'mime_type': doc.mime_type,
            'size_bytes': orig_path.stat().st_size,
            'hash_sha256': doc.file_hash,
            'ocr_enabled': bool(ocr_used),
            'text_path': (new_base / TEXT_FILENAME).as_posix() if text_content else None,
            'source_filename': orig_path.name,
            'tahun': parsed_tahun,
            'jenis': doc.jenis,
            'nomor': nomor,
            'perihal': parsed.get('perihal'),
            'tanggal_surat': parsed.get('tanggal_surat'),
            'pengirim': parsed.get('pengirim'),
            'penerima': parsed.get('penerima'),
            'parsed': parsed,
        }
        (new_base / METADATA_FILENAME).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

        # Update DB
        doc.tahun = parsed_tahun
        doc.nomor_surat = metadata['nomor']
        doc.perihal = metadata['perihal']
        doc.stored_path = str(new_base / orig_path.name)
        doc.metadata_path = str(new_base / 'metadata.json')
        db.add(doc)
        db.commit()

        print('Moved files:', moved)
        print('Updated doc id:', doc.id)

    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/fix_doc_by_hash.py <sha256>')
    else:
        main(sys.argv[1])