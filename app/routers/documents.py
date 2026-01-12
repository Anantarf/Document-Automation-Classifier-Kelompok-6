from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
import logging

from app.dependencies import get_db
from app.schemas import DocumentRead
from app.models import Document

log = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{doc_id}", response_model=DocumentRead, summary="Get document metadata")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/file", summary="Stream original document file")
def get_document_file(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    stored = Path(doc.stored_path)
    if not stored.exists() or not stored.is_file():
        raise HTTPException(status_code=404, detail="File not found on server")

    # Try to get original filename from metadata if available
    filename = stored.name
    try:
        meta_path = Path(doc.metadata_path)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            # Prefer original uploaded filename
            filename = meta.get("source_filename") or meta.get("file_original") or filename
    except Exception:
        pass

    def _stream():
        with stored.open("rb") as f:
            for chunk in iter(lambda: f.read(64 * 1024), b""):
                yield chunk

    return StreamingResponse(_stream(), media_type=doc.mime_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


class DocumentUpdate(BaseModel):
    perihal: Optional[str] = None
    nomor_surat: Optional[str] = None
    tahun: Optional[int] = None
    jenis: Optional[str] = None

@router.delete("/{doc_id}", summary="Delete document", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Optional: Delete file from disk
    # For safety, let's keep the file but remove the DB entry for now, 
    # or implementing hard delete if requested. User asked for 'Delete' management.
    # We will do hard delete for cleanup.
    try:
        if doc.stored_path:
            p = Path(doc.stored_path)
            if p.exists():
                p.unlink()
        if doc.metadata_path:
            m = Path(doc.metadata_path)
            if m.exists():
                m.unlink()
    except Exception as e:
        log.warning(f"Failed to delete files for doc {doc_id}: {e}")

    db.delete(doc)
    db.commit()
    return None

@router.patch("/{doc_id}", response_model=DocumentRead, summary="Update document metadata")
def update_document(doc_id: int, update_data: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if update_data.perihal is not None:
        doc.perihal = update_data.perihal
    if update_data.nomor_surat is not None:
        doc.nomor_surat = update_data.nomor_surat
    if update_data.tahun is not None:
        doc.tahun = update_data.tahun
    if update_data.jenis is not None:
        doc.jenis = update_data.jenis

    db.commit()
    db.refresh(doc)
    return doc

@router.get("/{doc_id}/text", summary="Get extracted OCR/text content as plain text")
def get_document_text(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Attempt to read metadata.json and find text_path
    try:
        meta_path = Path(doc.metadata_path)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            text_path = meta.get("text_path")
            if text_path:
                tp = Path(text_path)
                if tp.exists():
                    return PlainTextResponse(tp.read_text(encoding="utf-8"))
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Extracted text not available for this document")
