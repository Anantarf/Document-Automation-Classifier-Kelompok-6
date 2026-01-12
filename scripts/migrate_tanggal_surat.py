#!/usr/bin/env python
"""
Migrate tanggal_surat from metadata.json to database for existing documents.
This fixes the issue where tanggal_surat is NULL in database but populated in metadata.json
"""

import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

# Setup DB connection
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings, DB_FILE
from app.models import Base, Document

db_url = f"sqlite:///{DB_FILE}"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)

def migrate():
    """Populate tanggal_surat from metadata.json"""
    db = SessionLocal()
    try:
        docs = db.query(Document).filter(Document.tanggal_surat.is_(None)).all()
        updated_count = 0
        
        print(f"Found {len(docs)} documents with NULL tanggal_surat")
        
        for doc in docs:
            # Try to read from metadata.json
            try:
                meta_path = Path(doc.metadata_path)
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    tanggal = meta.get("tanggal_surat")
                    
                    if tanggal:
                        doc.tanggal_surat = tanggal
                        updated_count += 1
                        print(f"✓ Updated doc {doc.id} ({doc.nomor_surat}): tanggal_surat = {tanggal}")
                    else:
                        print(f"✗ Doc {doc.id} ({doc.nomor_surat}): no tanggal_surat in metadata")
                else:
                    print(f"✗ Doc {doc.id}: metadata file not found at {meta_path}")
            except Exception as e:
                print(f"✗ Error reading metadata for doc {doc.id}: {e}")
        
        db.commit()
        print(f"\n✅ Migration complete: {updated_count} documents updated")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
