
# app/routers/upload.py
"""
Endpoint upload dokumen + pipeline background:
- Terima DOCX/PDF
- Ekstraksi teks (DOCX/PDF teks) atau OCR (PDF scan)
- Ekstraksi metadata (nomor/perihal/tanggal/pengirim/penerima)
- Klasifikasi (surat_masuk / surat_keluar)
- Tentukan tahun
- Auto-foldering + metadata.json
- Simpan ke database + audit log
"""

import os
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Document, OCRText
from app.utils.hash import sha256_file
from app.utils.audit import log as audit_log
from app.services.parser_docx import extract_text_from_docx
from app.services.parser_pdf import extract_text_from_pdf
from app.services.ocr import ocr_pdf_to_text
from app.services.metadata import (
    extract_nomor_surat,
    extract_perihal,
    extract_tanggal,
    extract_pengirim_penerima,
    decide_tahun,
)
from app.services.classifier import classify
from app.services.foldering import target_dir, write_metadata

router = APIRouter(prefix="/upload", tags=["upload"])


def save_temp(file: UploadFile) -> str:
    """Simpan file upload ke folder sementara."""
    os.makedirs(settings.temp_upload_dir, exist_ok=True)
    temp_path = os.path.join(settings.temp_upload_dir, file.filename)
    with open(temp_path, "wb") as f:
        f.write(file.file.read())
    return temp_path


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    actor: str | None = None,
):
    """Menerima file dan menjadwalkan proses pipeline di background."""
    ext = (file.filename.split(".")[-1] or "").lower()
    if ext not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Format tidak didukung. Gunakan DOCX atau PDF.")

    temp_path = save_temp(file)

    # Hitung hash untuk mencegah duplikasi
    with open(temp_path, "rb") as fh:
        file_hash = sha256_file(fh)

    # Jadwalkan proses pipeline (agar response cepat)
    if background_tasks is not None:
        background_tasks.add_task(process_pipeline, temp_path, file.filename, file_hash, actor)
    return {"message": "File diterima, sedang diproses", "file": file.filename}


def process_pipeline(temp_path: str, filename: str, file_hash: str, actor: str | None):
    """Pipeline lengkap pemrosesan dokumen."""
    from app.database import SessionLocal

    session: Session = SessionLocal()
    try:
        # Cek duplikasi
        existing = session.query(Document).filter_by(file_hash=file_hash).first()
        if existing:
            audit_log(session, actor, "upload_duplicate", existing.id, f"Duplikasi: {filename}")
            os.remove(temp_path)
            return

        # Ekstraksi teks
        text = ""
        is_scanned = False
        if filename.lower().endswith(".docx"):
            text = extract_text_from_docx(temp_path)
        else:
            text, is_scanned = extract_text_from_pdf(temp_path)
            if is_scanned:
                text = ocr_pdf_to_text(temp_path)

        # Ekstraksi metadata
        nomor = extract_nomor_surat(text) or None
        perihal = extract_perihal(text) or None
        tanggal = extract_tanggal(text)
        ppl = extract_pengirim_penerima(text)

        # Klasifikasi & tahun
        jenis, confidence = classify(text)
        tahun = decide_tahun(tanggal, uploaded_at=datetime.utcnow())

        # Auto-foldering
        dir_path = target_dir(settings.storage_root, tahun, jenis, nomor, perihal)
        os.makedirs(dir_path, exist_ok=True)
        final_path = os.path.join(dir_path, "original." + filename.split(".")[-1])
        os.replace(temp_path, final_path)

        # Simpan DB
        doc = Document(
            file_name=filename,
            stored_path=final_path,
            file_hash=file_hash,
            jenis=jenis,
            tahun=tahun,
            nomor_surat=nomor,
            perihal=perihal,
            tanggal_surat=tanggal.date() if tanggal else None,
            confidence=confidence,
            status="processed",
            uploaded_by=actor,
        )
        session.add(doc)
        session.flush()

        # Simpan ocr_text (baik hasil parser maupun OCR)
        if text:
            ocr = OCRText(doc_id=doc.id, content=text)
            session.add(ocr)

        # metadata.json
        meta = {
            "jenis": jenis,
            "tahun": tahun,
            "nomor_surat": nomor,
            "perihal": perihal,
            "tanggal_surat": doc.tanggal_surat.isoformat() if doc.tanggal_surat else None,
            "pengirim": ppl.get("pengirim"),
            "penerima": ppl.get("penerima"),
            "confidence": confidence,
            "source_file": os.path.basename(final_path),
            "uploaded_by": actor,
            "uploaded_at": datetime.utcnow().isoformat(),
        }
        write_metadata(dir_path, meta)

        session.commit()
        audit_log(session, actor, "upload", doc.id, f"Upload {filename} → {doc.jenis}/{doc.tahun}")
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        audit_log(session, actor, "error", None, f"{filename}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    finally:
        session.close()
