# Arsip Kelurahan - Document Automation Classifier

Sistem manajemen arsip digital untuk **Kelurahan Pela Mampang** menggunakan FastAPI + SQLite + React.

Sistem ini otomatis mengklasifikasi, mengindeks, dan menyimpan dokumen surat masuk/keluar dengan ekstraksi metadata cerdas (OCR untuk PDF scan).

## ✨ Fitur Utama

- 📄 **Upload Dokumen**: DOCX & PDF dengan validasi otomatis
- 🔤 **Ekstraksi Teks**: Parser native + OCR Tesseract untuk PDF scan
- 🤖 **Klasifikasi Otomatis**: Surat masuk vs keluar (rule-based)
- 📊 **Parsing Metadata**: Nomor surat, tanggal, perihal, pengirim/penerima (regex)
- 📁 **Auto-Foldering**: Penyimpanan terstruktur per tahun/jenis surat
- 🔍 **Pencarian Metadata**: Filter berdasarkan tahun, jenis, nomor, perihal
- 📦 **Ekspor Data**: ZIP arsip per tahun/jenis + CSV metadata
- 🛡️ **Keamanan**: JWT authentication, CORS controlled
- 📱 **UI Modern**: React + Tailwind CSS responsive design

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 16+ (untuk frontend)
- (Optional) Tesseract-OCR untuk OCR support

### Setup Backend

```bash
# Clone repository
git clone https://github.com/Anantarf/Document-Automation-Classifier-Kelompok-6.git
cd Document-Automation-Classifier-Kelompok-6

# Buat virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# atau source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env dengan konfigurasi Anda

# Initialize database
python scripts/init_db.py

# Run backend
uvicorn app.main:app --reload
```

Backend akan berjalan di `http://127.0.0.1:8000`

### Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend akan berjalan di `http://localhost:5173`

## 📋 Default Login

- **Username**: `pelamampang`
- **Password**: `pelamampang123`

> ⚠️ Ubah password ini setelah first login di production!

## 📁 Struktur Direktori

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
- Internal model field `nomor` telah distandarkan menjadi **`nomor_surat`** pada kode & skema; DB **kolom** tetap `nomor` sehingga tidak perlu migrasi schema. Endpoint upload saat ini mengembalikan kedua kunci `nomor` (legacy) dan `nomor_surat` (kanonik) untuk kompatibilitas.
- SQLite memadai untuk single-PC/LAN. Jika skala bertambah, migrasi ke Postgres disarankan.

---

## OCR setup (Windows — recommended: PyMuPDF fallback)

Jika file PDF yang diunggah adalah hasil scan (gambar), sistem akan mencoba ekstraksi teks via OCR.
Untuk menggunakan OCR pada Windows, ikuti langkah berikut:

1. Install Python dependencies (di dalam virtualenv):

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

(Paket penting: `pytesseract`, `Pillow`, `PyMuPDF` — sudah tercantum di `requirements.txt`.)

2. Install Tesseract engine (Windows):

   - Unduh installer dari: https://github.com/tesseract-ocr/tesseract/releases
   - Secara default Tesseract akan terpasang di: `C:\Program Files\Tesseract-OCR\tesseract.exe`

3. Set Tesseract path di `.env`:

```dotenv
# Jika Tesseract tidak di PATH, isi path lengkap seperti contoh berikut
TESSERACT_CMD="C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

4. Restart server:

```powershell
uvicorn app.main:app --reload
```

5. Test OCR cepat:

```powershell
python scripts/test_ocr.py
```

Catatan:

- Jika kamu lebih suka `pdf2image` + `poppler`, kamu bisa menambah `pdf2image` ke environment, namun pada Windows `PyMuPDF` sering lebih mudah di-setup.
- Jika OCR tidak berjalan namun file memiliki metadata di filename (mis. `SM`/`SK` atau ada tahun), parser akan tetap mencoba ekstraksi dari filename/nomor sebagai fallback.

---

## Health check (opsional)

Untuk memeriksa status OCR dari aplikasi (apakah `pytesseract`, `PyMuPDF` tersedia, dan apakah `TESSERACT_CMD` terdeteksi), panggil endpoint:

```bash
curl http://127.0.0.1:8000/healthz/ocr
```

Contoh respons ketika OCR tersedia:

```json
{ "ocr": true, "details": { "pytesseract": true, "pymupdf": true, "tesseract_cmd": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe", "tesseract_cmd_exists": true, "tesseract_version": "4.1.1" } }
```

Jika `ocr` false, cek `README` bagian OCR setup dan pastikan Tesseract terinstal serta `TESSERACT_CMD` di `.env` mengarah ke executable yang benar.
