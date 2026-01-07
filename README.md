
# Document Automation Classifier (FastAPI + SQLite)

Sistem ringan untuk mengunggah dokumen **Word (DOCX)** dan **PDF**, mengekstrak teks (parser/OCR),
melakukan **klasifikasi otomatis** (surat_masuk / surat_keluar), mengekstrak **tahun**, dan **auto-foldering** arsip
per tahun dan jenis. Mendukung pencarian metadata, audit log, serta ekspor ZIP/CSV.

## Fitur Utama
- Upload DOCX/PDF (batch & single)
- Ekstraksi teks: langsung untuk DOCX/PDF teks; **OCR Tesseract** untuk PDF hasil scan
- Klasifikasi 2 label + confidence (rule-based + opsi ML ringan)
- Ekstraksi tahun, nomor surat, perihal, pengirim/penerima (regex)
- Auto-foldering + metadata.json
- Pencarian metadata (tahun, jenis, nomor_surat, perihal)
- Ekspor ZIP arsip per tahun/jenis & CSV metadata
- Audit log aktivitas

## Jalankan Lokal
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload
```

## Struktur Direktori
```
app/
  main.py              # Entry FastAPI
  config.py            # Settings (dotenv)
  database.py          # SQLAlchemy engine & session
  models.py            # SQLAlchemy models
  schemas.py           # Pydantic schemas
  routers/
    upload.py
    search.py
    export.py
  services/
    parser_docx.py
    parser_pdf.py
    ocr.py
    metadata.py
    classifier.py
    foldering.py
  utils/
    audit.py
    hash.py
    slugs.py
scripts/
  init_db.py           # Membuat folder & DB awal
storage/
  uploads/             # Temp upload
  arsip_kelurahan/     # Output akhir (tahun/jenis/...)
```

## Catatan
- Pastikan **Tesseract** terpasang dan dapat dipanggil; untuk Bahasa Indonesia gunakan traineddata `ind`.
- Untuk PDF teks, sistem akan parsing tanpa OCR; OCR hanya digunakan bila konten teks tidak terbaca.
- SQLite memadai untuk single-PC/LAN. Jika skala bertambah, migrasi ke Postgres disarankan.
