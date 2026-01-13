# Arsip Kelurahan - Document Automation Classifier

📦 **GitHub**: [https://github.com/Anantarf/Arsip-Digital-Kelurahan-Pela-Mampang](https://github.com/Anantarf/Arsip-Digital-Kelurahan-Pela-Mampang)

> ⚠️ **Note**: Sistem ini full-stack application (backend FastAPI + frontend React). GitHub Pages hanya untuk frontend statis. Untuk demo lengkap, run lokal dengan instruksi di bawah.

Sistem manajemen arsip digital untuk **Kelurahan Pela Mampang** menggunakan FastAPI + SQLite + React.

Sistem ini otomatis mengklasifikasi, mengindeks, dan menyimpan dokumen surat masuk/keluar dengan ekstraksi metadata cerdas (OCR untuk PDF scan).

## ✨ Fitur Utama

- 📄 **Upload Dokumen**: DOCX & PDF dengan validasi otomatis
- 🔤 **Ekstraksi Teks**: Parser native + OCR Tesseract untuk PDF scan
- 🤖 **Klasifikasi Otomatis**: Surat masuk vs keluar (rule-based + ML ready)
- 📊 **Parsing Metadata**: Nomor surat, tanggal, perihal, pengirim/penerima (regex)
- 📁 **Auto-Foldering**: Penyimpanan terstruktur per tahun/bulan/jenis
- 🔍 **Pencarian Canggih**: Hierarchical browser + global search
- 📥 **Preview Modal**: Full-screen document preview dengan metadata
- 📦 **Ekspor Data**: ZIP arsip per tahun/jenis + CSV metadata
- 🛡️ **Keamanan**: JWT authentication, role-based access control
- 📱 **UI Modern**: React + TypeScript + Tailwind CSS responsive design
- ⚡ **Performance**: React Query caching, optimistic updates

## 🛠️ Tech Stack

### Backend

- **Framework**: FastAPI 0.104.1 (Python 3.9+)
- **Database**: SQLite 3 with SQLAlchemy 2.0 ORM
- **Authentication**: JWT (HS256) with Bearer tokens
- **OCR**: Tesseract + pytesseract
- **PDF Processing**: PyMuPDF (fitz), PyPDF2
- **DOCX Processing**: python-docx
- **Machine Learning Ready**: Placeholder for classifier model (data/classifier.pkl)

### Frontend

- **Framework**: React 18.3 + TypeScript 5.6
- **Build Tool**: Vite 5.4.21
- **Styling**: Tailwind CSS 3.4
- **State Management**: React Query (TanStack Query) 4.34
- **Forms**: React Hook Form + react-dropzone
- **PDF Viewer**: react-pdf (pdfjs-dist 3.12.313)
- **Icons**: Lucide React
- **HTTP Client**: Axios with interceptors

### DevOps

- **Containerization**: Docker + Docker Compose
- **Web Server**: Uvicorn (ASGI)
- **CORS**: Configured for localhost development
- **Environment**: .env configuration

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


> ⚠️ **PENTING**: Ubah password ini setelah first login di production!

## 🐳 Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop containers
docker-compose down
```

Services akan tersedia di:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`

## 🌐 Production Deployment

### Backend

1. Update `.env` dengan production values:
   ```dotenv
   APP_ENV=production
   APP_DEBUG=false
   SECRET_KEY=<generate-strong-secret-key>
   CORS_ORIGINS=https://yourdomain.com
   ```
2. Use production ASGI server:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```
3. Setup Nginx reverse proxy
4. Enable HTTPS with SSL certificates

### Frontend

1. Build for production:
   ```bash
   cd frontend
   npm run build
   ```
2. Serve `dist/` folder with Nginx/Apache
3. Update `VITE_API_BASE` to production API URL
4. Configure CSP headers

### Database

- For production scale, consider migrating to PostgreSQL
- Setup regular backups (SQLite → `.db` file backup)
- Implement audit logging for compliance

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed production setup guide.

## 📋 Default Login

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

---

## 🧪 Testing

### Backend Tests

```bash
# Run unit tests
pytest tests/

# Test specific module
python tests/test_text_extractor.py
python tests/test_nomor_surat.py
```

### Frontend Tests

```bash
cd frontend

# Run unit tests
npm test

# Run with coverage
npm run test:coverage
```

## 🔧 Maintenance

- **Backup Database**: Copy `data/app.db` regularly
- **Clear Temp Files**: Cleanup `storage/uploads/` dan `storage/tmp_ocr/` periodically
- **Update ML Model**: Replace `data/classifier.pkl` with retrained model
- **Monitor Storage**: Check `storage/arsip_kelurahan/` disk usage

See [MAINTENANCE.md](MAINTENANCE.md) for detailed maintenance procedures.

## 📚 Documentation

- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **API Redoc**: `http://localhost:8000/redoc`
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Maintenance Guide**: [MAINTENANCE.md](MAINTENANCE.md)
- **Security Practices**: [SECURITY.md](SECURITY.md)

## 👥 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is for educational purposes (P3L - Informatika).



Made with ❤️ for Kelurahan Pela Mampang
