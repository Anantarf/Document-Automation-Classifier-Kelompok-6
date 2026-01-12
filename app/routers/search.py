
# app/routers/search.py
"""
Endpoint pencarian & filter dokumen berdasarkan metadata:
- tahun
- jenis ('masuk' | 'keluar')
- nomor / nomor_surat (LIKE, case-insensitive)
- perihal (LIKE, case-insensitive)
- limit & offset (opsional)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_db
from app.models import Document
from app.schemas import DocumentRead  # pastikan schema ini fields-nya match dengan model


router = APIRouter(prefix="/search", tags=["Search"])

@router.get("/stats", summary="Get dashboard stats")
def get_stats(db: Session = Depends(get_db)):
    total_docs = db.query(Document).count()
    masuk = db.query(Document).filter(Document.jenis == 'masuk').count()
    keluar = db.query(Document).filter(Document.jenis == 'keluar').count()
    return {
        "total_documents": total_docs,
        "surat_masuk": masuk,
        "surat_keluar": keluar
    }



@router.get("/", response_model=List[DocumentRead], summary="Cari dokumen")
def search_documents(
    tahun: Optional[int] = Query(None, description="Tahun surat (mis. 2025)"),
    jenis: Optional[str] = Query(None, description="Jenis surat: 'masuk' atau 'keluar'"),
    nomor: Optional[str] = Query(None, max_length=100, description="Nomor surat (partial match, case-insensitive, max 100 chars)"),
    nomor_surat: Optional[str] = Query(None, max_length=100, description="Alias untuk 'nomor' (partial match, max 100 chars)"),
    perihal: Optional[str] = Query(None, max_length=500, description="Perihal (partial match, case-insensitive, max 500 chars)"),
    bulan: Optional[str] = Query(None, description="Bulan (partial match in tanggal_surat, e.g. 'Januari')"),
    limit: int = Query(100, ge=1, le=1000, description="Batas jumlah hasil"),
    offset: int = Query(0, ge=0, description="Offset/paging"),
    sort_by: Optional[str] = Query(None, description="Kolom untuk sorting: 'uploaded_at'|'id'|'tahun'"),
    sort_dir: str = Query('desc', description="Arah sorting: 'asc' atau 'desc'"),
    db: Session = Depends(get_db),
    response: Response = None,
):
    # normalize sort_dir
    sort_dir = (sort_dir or 'desc').lower()
    if sort_dir not in {'asc', 'desc'}:
        sort_dir = 'desc'
    # Validasi jenis
    if jenis is not None and jenis not in {"masuk", "keluar", "lainnya"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="jenis harus 'masuk', 'keluar', atau 'lainnya'"
        )

    q = db.query(Document)

    if tahun is not None:
        q = q.filter(Document.tahun == tahun)

    if jenis:
        q = q.filter(Document.jenis == jenis)

    # Pakai alias: nomor OR nomor_surat
    nomor_term = nomor or nomor_surat
    if nomor_term:
        term = nomor_term.strip().lower()
        q = q.filter(func.lower(Document.nomor_surat).like(f"%{term}%"))

    # Filter Bulan logic
    # Expects string like "Januari", "Februari", etc.
    if bulan:
        term = bulan.strip().lower()
        # tanggal_surat is e.g. "12 Januari 2025" or "12-01-2025"??
        # Usually metadata sets it as "d B Y". 
        # So we look for the month name inside.
        q = q.filter(func.lower(Document.tanggal_surat).like(f"%{term}%"))

    if perihal:
        term = perihal.strip().lower()
        q = q.filter(func.lower(Document.perihal).like(f"%{term}%"))

    # Total count for pagination header
    total = q.count()

    # Sorting
    if sort_by in {'uploaded_at', 'id', 'tahun'}:
        col = getattr(Document, sort_by)
        if sort_dir == 'asc':
            q = q.order_by(col.asc())
        else:
            q = q.order_by(col.desc())
    else:
        # default ordering
        q = q.order_by(Document.uploaded_at.desc(), Document.id.desc())

    # Get total count BEFORE adding limit/offset
    total = q.count()

    rows = (
        q.offset(offset)
         .limit(limit)
         .all()
    )

    # Attach total in header for frontend pagination
    if response is not None:
        try:
            response.headers['X-Total-Count'] = str(total)
        except Exception:
            pass

    return rows


@router.get("/years", summary="Get available years")
def get_years(
    jenis: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(Document.tahun).distinct()
    if jenis:
        q = q.filter(Document.jenis == jenis)
    # Return list of ints, sorted desc
    years = [r[0] for r in q.all() if r[0]]
    return sorted(years, reverse=True)


@router.get("/months", summary="Get available months for year/jenis")
def get_months(
    tahun: int,
    jenis: str,
    db: Session = Depends(get_db)
):
    """
    Returns list of months (names) found in documents for specific year/jenis.
    Since tanggal_surat is string, we must fetch and parse distinct values.
    Supports both Indonesian and English month names.
    """
    # Optimized: fetch only needed columns
    docs = db.query(Document.tanggal_surat).filter(
        Document.tahun == tahun,
        Document.jenis == jenis,
        Document.tanggal_surat.isnot(None)
    ).all()

    # Set of found months
    found_months = set()
    
    # Month names mapping: both Indonesian and English
    MONTHS_MAPPING = {
        "Januari": "January", "Februari": "February", "Maret": "March",
        "April": "April", "Mei": "May", "Juni": "June",
        "Juli": "July", "Agustus": "August", "September": "September",
        "Oktober": "October", "November": "November", "Desember": "December"
    }
    
    # All month names to search for (both languages)
    ALL_MONTHS_ID = list(MONTHS_MAPPING.keys())
    ALL_MONTHS_EN = list(MONTHS_MAPPING.values())
    ALL_MONTH_NAMES = ALL_MONTHS_ID + ALL_MONTHS_EN
    
    for (t_str,) in docs:
        if not t_str: 
            continue
        t_lower = t_str.lower()
        
        # Try to find any month name (Indonesian or English)
        for m in ALL_MONTH_NAMES:
            if m.lower() in t_lower:
                # Return Indonesian name for UI consistency
                found_month = m if m in ALL_MONTHS_ID else [k for k, v in MONTHS_MAPPING.items() if v == m][0]
                found_months.add(found_month)
                break
    
    # Sort them chronologically using Indonesian month order
    sorted_months = sorted(list(found_months), key=lambda x: ALL_MONTHS_ID.index(x))
    return sorted_months
