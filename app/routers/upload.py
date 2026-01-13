
# app/routers/upload.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
import hashlib
import json
import re
from pydantic import BaseModel

from app.dependencies import get_db
from app.config import settings
from app.models import Document
from app.services.text_extraction import extract_text_and_save
from app.services.metadata import parse_metadata
from app.utils.slugs import slugify_nomor
from app.constants import METADATA_FILENAME, TEXT_FILENAME

router = APIRouter()

from app.constants import ALLOWED_MIME


class PredictRequest(BaseModel):
    text: str
    jenis_hint: str | None = None

# Use `slugify_nomor` from `app.utils.slugs` for nomor normalization

# Helper function to extract month name from tanggal_surat
def extract_bulan(tanggal_surat: str | None) -> str | None:
    """Extract Indonesian month name from tanggal_surat string."""
    if not tanggal_surat:
        return None
    
    MONTHS = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    MONTHS_EN = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    tanggal_lower = tanggal_surat.lower()
    
    # Check Indonesian months
    for month in MONTHS:
        if month.lower() in tanggal_lower:
            return month
    
    # Check English months and convert to Indonesian
    for i, month_en in enumerate(MONTHS_EN):
        if month_en.lower() in tanggal_lower:
            return MONTHS[i]
    
    return None

@router.post("/upload/", summary="Unggah DOCX/PDF (auto kategori tahun & jenis)", tags=["Upload"])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    tahun: int | None = Form(None),            # opsional: auto dari parser
    jenis: str | None = Form(None),            # opsional: auto ('masuk' | 'keluar')
    nomor: str | None = Form(None),            # opsional: auto
    perihal: str | None = Form(None),          # opsional: auto
    tanggal_surat: str | None = Form(None),    # opsional: auto
    pengirim: str | None = Form(None),
    penerima: str | None = Form(None),
    db: Session = Depends(get_db),
):
    # --- Validasi MIME ---
    ext = ALLOWED_MIME.get(file.content_type)
    if not ext:
        raise HTTPException(status_code=415, detail="Only DOCX/PDF allowed")

    # --- Baca file & hash ---
    content = await file.read()
    size_bytes = len(content)
    
    # --- Validasi ukuran file ---
    from app.constants import MAX_UPLOAD_SIZE
    if size_bytes > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File terlalu besar (max {MAX_UPLOAD_SIZE / (1024*1024):.0f} MB)")
    
    sha256 = hashlib.sha256(content).hexdigest()

    # --- Cek duplikasi by hash ---
    existing = db.query(Document).filter(Document.file_hash == sha256).first()
    if existing:
        raise HTTPException(status_code=409, detail="File yang sama sudah pernah diunggah (hash duplikat)")

    now_utc = datetime.utcnow()

    # --- Ekstrak teks di folder temp ---
    temp_dir: Path = settings.TEMP_UPLOAD_PATH
    temp_dir.mkdir(parents=True, exist_ok=True)
    text_path, text_content, ocr_used = extract_text_and_save(
        content=content,
        mime_type=file.content_type,
        base_dir=temp_dir,
    )

    # --- Parse metadata dari teks + nama file ---
    parsed = parse_metadata(text_content or "", file.filename, uploaded_at=now_utc)

    # --- Tentukan nilai final (input menang jika diisi) ---
    nomor_final = (nomor or parsed.get("nomor")) or "TANPA-NOMOR"
    perihal_final = (perihal or parsed.get("perihal")) or "Tidak ada perihal"
    tanggal_final = tanggal_surat or parsed.get("tanggal_surat")
    
    # Extract bulan (month) from tanggal_surat for categorization
    bulan_final = extract_bulan(tanggal_final)

    # Tahun: prefer nilai input yang valid (positive int). Jika input kosong/0, fallback ke parsed.
    # Jika tidak terdeteksi, biarkan None untuk disimpan di luar folder tahun.
    try:
        if tahun and int(tahun) > 0:
            tahun_final = int(tahun)
        else:
            tahun_final = parsed.get("tahun")

        # Pastikan tahun_final valid (positive integer). Jika tidak ada, set None.
        if tahun_final is None or int(tahun_final) <= 0:
            tahun_final = None  # Document will be stored directly in jenis folder
        else:
            tahun_final = int(tahun_final)
    except (ValueError, TypeError):
        # Jika parsing gagal, set None
        tahun_final = None

    # Jenis: input -> parsed -> fallback kecil -> default 'keluar'
    jenis_final = jenis or parsed.get("jenis")
    if jenis_final is None:
        if re.search(r"(?i)(?:^|/|[-_])SM(?:/|[-_]|$)", nomor_final):
            jenis_final = "masuk"
        elif re.search(r"(?i)(?:^|/|[-_])SK(?:/|[-_]|$)", nomor_final):
            jenis_final = "keluar"
    if jenis_final not in {"masuk", "keluar"}:
        jenis_final = "keluar"

    # --- Foldering: different structure for invalid docs ---
    slug = slugify_nomor(nomor_final)
    if tahun_final and bulan_final:
        # Valid document: store in tahun/jenis/slug structure
        base_dir: Path = settings.STORAGE_ROOT_DIR / str(tahun_final) / jenis_final / slug
    else:
        # Invalid document (no tahun or bulan): store directly in jenis/slug
        base_dir: Path = settings.STORAGE_ROOT_DIR / jenis_final / slug
    base_dir.mkdir(parents=True, exist_ok=True)

    # --- Simpan file asli ---
    original_name = f"original.{ext}"
    original_path = base_dir / original_name
    original_path.write_bytes(content)

    # --- Simpan text.txt (kalau ada) ---
    final_text_path = None
    if text_content:
        final_text_path = base_dir / TEXT_FILENAME
        final_text_path.write_text(text_content, encoding="utf-8")

    # --- Siapkan metadata.json ---
    metadata_path = base_dir / METADATA_FILENAME
    metadata = {
        "uploaded_at": now_utc.isoformat() + "Z",
        "file_original": original_name,
        "mime_type": file.content_type,
        "size_bytes": size_bytes,
        "hash_sha256": sha256,
        "ocr_enabled": bool(settings.TESSERACT_CMD) or ocr_used,
        "text_path": final_text_path.as_posix() if final_text_path else None,
        "source_filename": file.filename,
    }
    metadata.update({
        "tahun": tahun_final,
        "jenis": jenis_final,
        "nomor": nomor_final,
        "perihal": perihal_final,
        "tanggal_surat": tanggal_final,
        "pengirim": pengirim or parsed.get("pengirim"),
        "penerima": penerima or parsed.get("penerima"),
        "parsed": parsed,
    })
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- Simpan ke SQLite ---
    doc = Document(
        tahun=tahun_final,
        jenis=jenis_final,
        nomor_surat=nomor_final,
        perihal=perihal_final,
        tanggal_surat=tanggal_final,
        bulan=bulan_final,
        pengirim=metadata["pengirim"],
        penerima=metadata["penerima"],
        stored_path=original_path.as_posix(),
        metadata_path=metadata_path.as_posix().replace("\\", "/"),
        uploaded_at=now_utc,
        mime_type=file.content_type,
        file_hash=sha256,
        ocr_enabled=metadata["ocr_enabled"],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # --- Bersihkan file text temp (best-effort) ---
    try:
        if text_path: text_path.unlink(missing_ok=True)
    except Exception:
        pass

    # --- Respons ---
    return {
        "id": doc.id,
        "message": "uploaded",
        "tahun": tahun_final,
        "jenis": jenis_final,
        "nomor": nomor_final,               # legacy key (backward compatibility)
        "nomor_surat": nomor_final,        # canonical key
        "perihal": perihal_final,
        "stored_path": doc.stored_path,
        "metadata_path": doc.metadata_path,
        "mime_type": file.content_type,
        "size": size_bytes,
        "hash": f"sha256:{sha256}",
        "parsed": parsed,
    }


@router.post("/upload/analyze", summary="Analyze file metadata without saving", tags=["Upload"])
async def analyze_document(
    file: UploadFile = File(...),
):
    # --- Validasi MIME ---
    ext = ALLOWED_MIME.get(file.content_type)
    if not ext:
        raise HTTPException(status_code=415, detail="Only DOCX/PDF allowed")

    # --- Baca content ---
    content = await file.read()
    
    # --- Estrak Teks (Temp) ---
    temp_dir: Path = settings.TEMP_UPLOAD_PATH
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Gunakan extract_text_and_save tapi kita hapus hasilnya nanti
    text_path, text_content, ocr_used = extract_text_and_save(
        content=content,
        mime_type=file.content_type,
        base_dir=temp_dir,
    )
    
    # --- Parse Metadata ---
    parsed = parse_metadata(text_content or "", file.filename, uploaded_at=datetime.utcnow())
    
    # Clean up temp text file immediately
    try:
        if text_path and text_path.exists():
            text_path.unlink()
    except Exception:
        pass
        
    return {
        "filename": file.filename,
        "parsed": parsed,
        "ocr_used": ocr_used,
        "preview_supported": True 
    }


@router.post("/predict-jenis")
async def predict_jenis(request: PredictRequest):
    """Predict document type (masuk/keluar) using ML classifier or rules."""
    from app.services.classifier_ml import classify
    
    try:
        jenis, confidence = classify(request.text)
        return {
            "predicted_jenis": jenis,
            "confidence": confidence,
            "method": "ml" if confidence > 0.7 else "rule-based"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification error: {str(e)}")
