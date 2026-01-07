
# app/routers/search.py
"""
Endpoint pencarian & filter dokumen berdasarkan metadata:
- tahun
- jenis (surat_masuk / surat_keluar)
- nomor_surat (LIKE)
- perihal (LIKE)
"""

from fastapi import APIRouter
from sqlalchemy.orm import Session
from app.models import Document
from app.schemas import DocumentRead

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/", response_model=list[DocumentRead])
def search_documents(
    tahun: int | None = None,
    jenis: str | None = None,
    nomor_surat: str | None = None,
    perihal: str | None = None,
):
    from app.database import SessionLocal

    session: Session = SessionLocal()
    try:
        q = session.query(Document)
        if tahun is not None:
            q = q.filter(Document.tahun == tahun)
        if jenis:
            q = q.filter(Document.jenis == jenis)
        if nomor_surat:
            q = q.filter(Document.nomor_surat.like(f"%{nomor_surat}%"))
        if perihal:
            q = q.filter(Document.perihal.like(f"%{perihal}%"))
        rows = q.order_by(Document.uploaded_at.desc()).all()
        return rows
    finally:
        session.close()
