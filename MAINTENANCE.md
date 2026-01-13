# Project Maintenance Guide

## Quick Start

### Run the system

```bash
.\run.bat
```

Backend: http://localhost:8000  
Frontend: http://localhost:5173

### Stop the system

```bash
Ctrl+C in terminal
```

---

## Directory Structure

```
├── app/                          # Main FastAPI application
│   ├── routers/                  # API endpoints
│   │   ├── upload.py            # Upload & auto-classification
│   │   ├── search.py            # Document search & filtering
│   │   ├── export.py            # Export documents
│   │   ├── health.py            # Health checks
│   │   └── auth.py              # Authentication
│   ├── services/                # Business logic
│   │   ├── classifier_ml.py     # ML classification (masuk/keluar)
│   │   ├── text_extraction.py   # PDF/DOCX text extraction
│   │   ├── metadata.py          # Parse document metadata
│   │   ├── ocr.py               # Tesseract OCR integration
│   │   ├── parser_pdf.py        # PDF parsing
│   │   ├── parser_docx.py       # DOCX parsing
│   │   └── foldering.py         # Folder structure logic
│   ├── utils/                   # Utilities
│   │   ├── slugs.py            # URL slug generation
│   │   ├── hash.py             # File hashing
│   │   ├── fileops.py          # File operations
│   │   └── audit.py            # Audit logging
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic validation schemas
│   ├── database.py             # Database connection
│   ├── config.py               # Configuration settings
│   ├── dependencies.py         # FastAPI dependencies
│   ├── main.py                 # App initialization & routing
│   └── constants.py            # Constants & configuration
├── scripts/                     # Administrative scripts
│   ├── train_classifier.py     # Train ML model (50-100+ docs needed)
│   ├── generate_training_data.py # Generate synthetic training data
│   ├── test_ocr.py             # Test OCR functionality
│   └── cleanup_invalid_docs.py # Remove invalid documents
├── frontend/                    # React + TypeScript UI
│   ├── src/
│   │   ├── pages/              # Page components
│   │   ├── components/         # Reusable components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── contexts/           # React context (auth, notifications)
│   │   ├── api/                # API calls
│   │   └── types/              # TypeScript types
│   └── vite.config.ts          # Vite configuration
├── storage/                     # Document storage
│   ├── arsip_kelurahan/        # Archive folder structure
│   │   ├── 2025/
│   │   │   ├── masuk/          # Incoming documents
│   │   │   ├── keluar/         # Outgoing documents
│   │   │   └── backup/         # Backups
│   │   ├── tmp_ocr/            # Temporary OCR output
│   │   └── uploads/            # Upload temp storage
├── data/                        # ML models & data
│   └── classifier_model.pkl    # Trained ML classifier model
├── tests/                       # Unit tests
└── docs/                        # Documentation

```

---

## Core Services Explained

### 1. ML Classifier (`classifier_ml.py`)

**Purpose**: Auto-classify documents as masuk (incoming) or keluar (outgoing)

**How it works**:

- Loads pre-trained model from `data/classifier_model.pkl`
- Uses TF-IDF vectorization + Multinomial Naive Bayes
- Falls back to rule-based if confidence < 70%

**Accuracy**: 100% on 100 training documents (synthetic + real)

**Usage**:

```python
from app.services.classifier_ml import classify
jenis, confidence = classify("Surat keputusan kepala desa")
# Returns: ("keluar", 0.91)
```

### 2. Text Extraction (`text_extraction.py`)

**Purpose**: Extract text from PDF/DOCX files

**Supports**:

- **PDF**: Uses pdfminer (fast, reliable)
- **DOCX**: Uses python-docx (native parsing)
- **Scanned PDFs**: Uses Tesseract OCR (optional)

### 3. Metadata Parser (`metadata.py`)

**Purpose**: Extract structured metadata from document text

**Extracts**:

- Document number (nomor_surat)
- Date (tanggal_surat → tahun + bulan)
- Description (perihal)
- Sender/recipient

### 4. Foldering System (`foldering.py`)

**Purpose**: Auto-organize documents into folder structure

**Valid documents** (with tahun & bulan):

```
storage/2025/masuk/SK-001-2025/
```

**Invalid documents** (no tahun/bulan):

```
storage/masuk/SK-UNKNOWN/
```

---

## Key Workflows

### Upload Document

1. User uploads PDF/DOCX via frontend
2. Backend extracts text (OCR if needed)
3. Classifier predicts jenis (masuk/keluar)
4. Metadata parser extracts: nomor, tahun, bulan, perihal
5. Auto-organize to correct folder
6. Save to database

### Search Documents

1. Filter by: jenis, tahun, bulan, nomor_surat, perihal
2. Return matching documents with file paths
3. Frontend creates preview/download links

### Train ML Model

1. Collect documents from database
2. TF-IDF vectorization (1000 features, 1-2 grams)
3. Multinomial Naive Bayes training
4. Save model to `data/classifier_model.pkl`
5. Restart backend to load new model

---

## Database Schema

### Document Table

```sql
CREATE TABLE document (
    id INTEGER PRIMARY KEY,
    tahun INTEGER,                    -- Year (nullable for invalid docs)
    jenis VARCHAR(50),                -- masuk or keluar
    nomor_surat VARCHAR(100),         -- Document number
    perihal TEXT,                     -- Description
    tanggal_surat VARCHAR(100),       -- Full date string
    bulan VARCHAR(20),                -- Extracted month (Januari, Februari, etc.)
    pengirim VARCHAR(255),            -- Sender
    penerima VARCHAR(255),            -- Recipient
    stored_path TEXT,                 -- File path
    metadata_path TEXT,               -- Metadata JSON path
    uploaded_at DATETIME,             -- Upload timestamp
    mime_type VARCHAR(50),            -- MIME type (application/pdf, etc.)
    file_hash VARCHAR(256),           -- SHA256 hash
    ocr_enabled BOOLEAN               -- Was OCR used?
)
```

---

## Important Scripts

### Train ML Classifier

```bash
python scripts/train_classifier.py
```

- Collects documents from database
- Trains TF-IDF + Naive Bayes model
- Saves to `data/classifier_model.pkl`
- **Requires**: 10+ documents (50+ recommended)

### Generate Synthetic Training Data

```bash
python scripts/generate_training_data.py
```

- Creates realistic document variations
- Target: 50 masuk + 50 keluar documents
- Saves to database & storage

### Test OCR

```bash
python scripts/test_ocr.py
```

- Verifies Tesseract installation
- Tests OCR on sample PDF

### Cleanup Invalid Documents

```bash
python scripts/cleanup_invalid_docs.py
```

- Removes documents with invalid tahun/bulan
- Cleans up storage folders

---

## Configuration

### Environment Variables (`.env`)

```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./app.db
TESSERACT_PATH=C:/Program Files/Tesseract-OCR/tesseract.exe
```

### Constants (`app/constants.py`)

- ALLOWED_MIME: Supported file types
- METADATA_FILENAME: Default metadata.json
- TEMP_UPLOAD_PATH: Temporary upload directory
- PDF2IMAGE_DPI: OCR resolution

---

## Common Issues & Solutions

### Issue: ML model not predicting

**Solution**:

1. Check `data/classifier_model.pkl` exists
2. Verify scikit-learn version: `pip list | grep scikit`
3. Restart backend: `.\run.bat`

### Issue: OCR not working

**Solution**:

1. Install Tesseract: See `INSTALL_OCR.md`
2. Update path in `.env`
3. Test: `python scripts/test_ocr.py`

### Issue: Documents not auto-classifying

**Solution**:

1. Check classifier is loaded: Look for "ML classifier loaded" in backend logs
2. Verify 100+ documents in database for training
3. Re-run training: `python scripts/train_classifier.py`

### Issue: Frontend can't upload files

**Solution**:

1. Check backend is running: `http://localhost:8000/healthz`
2. Verify CORS is enabled in `main.py`
3. Check browser console for exact error

---

## Performance Optimization

### Database

- Already indexed: jenis, tahun, bulan, nomor_surat
- Use pagination: `?limit=20&offset=0`

### Text Extraction

- PDF parsing is fast (< 1s for most files)
- OCR is slow (~5-30s per page), use sparingly

### ML Classification

- Model load time: ~2 seconds
- Classification per document: ~10ms

---

## Maintenance Checklist

- [ ] Weekly: Check error logs in console
- [ ] Monthly: Validate document classification accuracy
- [ ] Quarterly: Collect new training data & re-train model
- [ ] Yearly: Archive old documents to backup storage

---

## Development Workflow

### Add New Endpoint

1. Create route in `app/routers/`
2. Add service logic in `app/services/`
3. Test with curl/Postman
4. Update docs

### Modify ML Classification

1. Update `app/services/classifier_ml.py`
2. Collect training data with `scripts/generate_training_data.py`
3. Train: `python scripts/train_classifier.py`
4. Restart backend

### Debug Issues

1. Check backend terminal output
2. Enable logging in `app/config.py`
3. Review database state: Check `app.db` directly
4. Test endpoints with curl

---

## Contact & Support

For issues or improvements, document them in a GitHub issue or update this guide.

Last updated: January 13, 2026
