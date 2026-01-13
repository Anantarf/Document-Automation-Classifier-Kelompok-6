
# app/services/metadata.py
"""
Ekstraksi metadata (nomor surat, perihal, tanggal, pengirim/penerima, tahun, jenis).
Disesuaikan untuk pola surat Kelurahan DKI:
- Nomor contoh: 655-HM.03.04 (OCR bisa memberi '/-' -> dibersihkan).
- Label umum: Nomor, Sifat, Lampiran, Hal/Perihal.
- Tanggal format Indonesia: 12 Desember 2025.
- Jenis: 'masuk' vs 'keluar' - uses ML classifier if available, otherwise heuristics.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Optional

log = logging.getLogger(__name__)

# Try to import ML classifier
try:
    from app.services.classifier_ml import classify as ml_classify
    USE_ML_CLASSIFIER = True
    log.info("✅ ML Classifier available for metadata extraction")
except ImportError:
    USE_ML_CLASSIFIER = False
    log.info("ℹ️  Using rule-based classification (ML classifier not available)")

BULAN_ID = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
}


def _clean_text(text: str) -> str:
    # Bersihkan noise OCR umum dan normalisasi spasi
    t = (text or "").replace("/-", "-")
    t = re.sub(r"[ \t]+", " ", t)
    return t


def extract_sifat_surat(text: str) -> Optional[str]:
    """
    Ekstrak Sifat Surat (Penting, Biasa, Rahasia, dll).
    Hanya relevan untuk surat keluar.
    """
    T = _clean_text(text)
    # Cari pola "Sifat : Biasa/Penting/Rahasia"
    # Kadang OCR baca "Sifat :" jadi "Sifat =" atau "Sitat"
    m = re.search(r"(?i)\b(Sifat|Sibat|Sitat)\b\s*[:=]?\s*([A-Za-z]+)", T)
    if m:
        sifat = m.group(2).strip()
        # Validasi sederhana: hanya ambil jika panjang kata masuk akal
        if 3 < len(sifat) < 15:
            return sifat.capitalize()
    return None

def extract_nomor_surat(text: str, filename: Optional[str] = None) -> Optional[str]:
    """
    Ekstrak nomor surat (contoh: 655-HM.03.04, 123/SK/2025, dll).
    Pola: angka + tanda pemisah + kode instansi
    """

    T = _clean_text(text)

    # 1) 'Nomor: ...'
    m = re.search(r"(?i)\b(No|Nomor|Nemor|Nomer)\b[\s:.;]*([A-Za-z0-9./\-]+)", T)
    if m:
        nomor = m.group(2).strip()
        nomor = nomor.strip(".,;:/-")
        if len(nomor) > 3:
             return nomor

    # 2) Token kode di header
    lines = [l.strip() for l in T.splitlines()]
    for l in lines[:15]:
        tokens = l.split()
        for token in tokens:
             if re.match(r"^[A-Za-z0-9./\-]{4,}$", token) and re.search(r"\d", token) and re.search(r"[./\-]", token):
                 if not re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", token):
                    return token.strip(".,;")

    # 3) Fallback filename
    if filename:
        name = filename.rsplit(".", 1)[0]
        # Ambil kata pertama sebagai potensi nomor jika mengandung digit
        parts = name.split(maxsplit=1)
        if parts and re.search(r"\d", parts[0]) and len(parts[0]) > 3:
             return parts[0].strip()

    return None


def extract_perihal(text: str, filename: Optional[str] = None) -> Optional[str]:
    """
    Perihal dari:
      - 'Hal: ...' atau 'Perihal: ...'
      - Fallback: baris yang mengandung kata kunci umum (Permohonan, Balasan, Undangan, Disposisi)
      - Fallback filename: 'KODE PERIHAL.pdf' -> ambil PERIHAL
    """
    T = _clean_text(text)

    # Label langsung
    m = re.search(r"(?i)\b(Hal|Perihal)\b\s*[:\-]?\s*(.+)", T)
    if m:
        return re.split(r"\n", m.group(2))[0].strip()

    # Kata kunci umum
    keywords = r"(Permohonan|Balasan|Undangan|Disposisi|Pemberitahuan|Pengajuan|Laporan|Surat)"
    for l in T.splitlines():
        if re.search(rf"(?i)\b{keywords}\b", l):
            return l.strip()

    # Fallback filename
    if filename:
        name = filename.rsplit(".", 1)[0]
        mm = re.match(r"^\s*[A-Za-z0-9.\-\/]+\s+(.+)$", name)
        if mm:
            return mm.group(1).strip()

    return None


def extract_tanggal(text: str) -> Optional[datetime]:
    """
    Format: '12 Desember 2025' atau 'Jakarta, 12 Desember 2025'
    Fallback: hanya tahun (20xx) -> tanggal 1 Januari tahun tsb.
    """
    T = _clean_text(text)
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})", T, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3))
        month = BULAN_ID.get(month_name)
        if month:
            try:
                return datetime(year, month, day)
            except Exception:
                return None

    y = re.search(r"\b(20\d{2})\b", T)
    if y:
        return datetime(int(y.group(1)), 1, 1)
    return None


def extract_pengirim_penerima(text: str) -> Dict[str, Optional[str]]:
    """
    Heuristik sederhana:
      - Penerima dari 'Kepada Yth ...'
      - Pengirim dari 'Dari:'/ 'Pengirim:'
    """
    T = _clean_text(text)
    pengirim = None
    penerima = None

    m_to = re.search(r"(?i)\bKepada\b\s+Yth\.?\s*(.+)", T)
    if m_to:
        penerima = re.split(r"\n", m_to.group(1))[0].strip()

    m_from = re.search(r"(?i)\b(Dari|Pengirim)\b\s*:\s*(.+)", T)
    if m_from:
        pengirim = re.split(r"\n", m_from.group(2))[0].strip()

    return {"pengirim": pengirim, "penerima": penerima}


def decide_tahun(
    tanggal: Optional[datetime],
    uploaded_at: datetime,
    nomor: Optional[str] = None,
    filename: Optional[str] = None,
) -> int:
    """
    Urutan fallback menentukan tahun:
      1) dari tanggal (jika ada)
      2) dari nomor (angka 20xx)
      3) dari filename (angka 20xx)
      4) dari uploaded_at
    """
    if tanggal:
        return tanggal.year

    if nomor:
        m = re.search(r"\b(20\d{2})\b", nomor)
        if m:
            return int(m.group(1))

    if filename:
        m = re.search(r"\b(20\d{2})\b", filename)
        if m:
            return int(m.group(1))

    return uploaded_at.year


def detect_jenis(text: str, nomor: Optional[str] = None, filename: Optional[str] = None) -> Optional[str]:
    """
    Deteksi jenis surat (masuk atau keluar).
    1. Try ML classifier if available (confidence > 0.7)
    2. Fallback to heuristics: KOP detection, nomor patterns, filename
    """
    # Try ML classifier first if available and text is sufficient
    if USE_ML_CLASSIFIER and text and len(text.strip()) > 50:
        try:
            jenis, confidence = ml_classify(text)
            # Use ML prediction if high confidence
            if confidence > 0.7:
                log.info(f"ML Classifier: {jenis} (confidence: {confidence:.2%})")
                return jenis
            else:
                log.debug(f"ML Classifier low confidence ({confidence:.2%}), using rules")
        except Exception as e:
            log.warning(f"ML classification failed: {e}, falling back to rules")
    
    # Fallback to rule-based heuristics
    T = _clean_text(text)
    
    # --- Rule 1 Only: Kop Detection for Pela Mampang ---
    # Cari di 20 baris pertama (header)
    lines = T.splitlines()[:20]
    header_text = " ".join(lines).upper()

    # Cek eksistensi Kop "KELURAHAN PELA MAMPANG"
    has_kop_pela_mampang = ("KELURAHAN PELA MAMPANG" in header_text) or \
                           ("PEMERINTAH KOTA ADMINISTRASI JAKARTA SELATAN" in header_text and "KECAMATAN MAMPANG PRAPATAN" in header_text)

    if has_kop_pela_mampang:
        return "keluar"
    
    # Jika ada teks panjang di header tapi BUKAN Pela Mampang -> Masuk (dari instansi lain)
    # Asumsi: Header surat biasanya ada "PEMERINTAH..." atau "KEMENTERIAN..."
    if "PEMERINTAH" in header_text or "KEMENTERIAN" in header_text or "DEWAN" in header_text or "PT." in header_text:
        return "masuk"

    # --- Fallback (Jika OCR Header Gagal/Tidak Ada Kop) ---
    
    # Cek Nomor (Helper)
    if nomor:
        if re.search(r"(?i)(?:^|/|[-_])SM(?:/|[-_]|$)", nomor):
            return "masuk"
        if re.search(r"(?i)(?:^|/|[-_])SK(?:/|[-_]|$)", nomor):
            return "keluar"

    # Cek Filename (Helper)
    if filename:
        name = filename.rsplit(".", 1)[0]
        if re.search(r"(?i)(?:^|/|[-_])SM(?:/|[-_]|$)", name) or re.search(r"(?i)\bmasuk\b", name):
            return "masuk"
        if re.search(r"(?i)(?:^|/|[-_])SK(?:/|[-_]|$)", name) or re.search(r"(?i)\bkeluar\b", name):
            return "keluar"
    
    # Default ke Lainnya (jika tidak terdeteksi pola surat umum)
    return "lainnya"


def parse_metadata(text: str, filename: Optional[str], uploaded_at: datetime) -> Dict[str, Optional[str]]:
    """
    Parser terpadu untuk satu surat.
    """
    nomor = extract_nomor_surat(text, filename)
    sifat = extract_sifat_surat(text)
    perihal = extract_perihal(text, filename)
    dt = extract_tanggal(text)
    tanggal_str = dt.strftime("%d %B %Y") if dt and dt.day != 1 else (dt.strftime("%Y") if dt else None)

    tahun = decide_tahun(dt, uploaded_at, nomor, filename)
    jenis = detect_jenis(text, nomor, filename)
    peng_pener = extract_pengirim_penerima(text)

    return {
        "nomor": nomor,       # Real Number for DB/Slug
        "sifat": sifat,       # Sifat for UI display if needed
        "perihal": perihal,
        "tanggal_surat": tanggal_str,
        "tahun": tahun,
        "jenis": jenis,
        "pengirim": peng_pener.get("pengirim"),
        "penerima": peng_pener.get("penerima"),
    }
