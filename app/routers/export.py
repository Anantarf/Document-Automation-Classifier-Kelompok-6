
# app/routers/export.py
"""
Ekspor arsip ZIP & CSV metadata:
- /export/zip?tahun=YYYY&jenis=surat_masuk|surat_keluar
- /export/csv?tahun=YYYY&jenis=...
"""

import os, io, csv, zipfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Document

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/zip")
def export_zip(tahun: int, jenis: str):
    if jenis not in ("surat_masuk", "surat_keluar"):
        raise HTTPException(status_code=400, detail="Jenis tidak valid")
    root = os.path.join(settings.storage_root, str(tahun), jenis)
    if not os.path.isdir(root):
        raise HTTPException(status_code=404, detail="Arsip tidak ditemukan")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(base, f)
                arcname = os.path.relpath(p, root)  # relative path dalam ZIP
                z.write(p, arcname)
    buffer.seek(0)
    filename = f"arsip_{tahun}_{jenis}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/csv")
def export_csv(tahun: int | None = None, jenis: str | None = None):
    from app.database import SessionLocal
    session: Session = SessionLocal()
    try:
        q = session.query(Document)
        if tahun:
            q = q.filter(Document.tahun == tahun)
        if jenis:
            q = q.filter(Document.jenis == jenis)
        rows = q.order_by(Document.uploaded_at.asc()).all()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "id","file_name","stored_path","jenis","tahun",
            "nomor_surat","perihal","tanggal_surat","confidence",
            "status","uploaded_by","uploaded_at"
        ])
        for d in rows:
            writer.writerow([
                d.id, d.file_name, d.stored_path, d.jenis, d.tahun,
                d.nomor_surat or "", d.perihal or "",
                d.tanggal_surat.isoformat() if d.tanggal_surat else "",
                d.confidence or "", d.status, d.uploaded_by or "",
                d.uploaded_at.isoformat()
            ])
        buffer.seek(0)
        filename = f"metadata_{tahun or 'all'}_{jenis or 'all'}.csv"
        return StreamingResponse(
            io.BytesIO(buffer.read().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    finally:
        session.close()
