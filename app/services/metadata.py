
# app/services/metadata.py
"""
Ekstraksi metadata (nomor surat, perihal, tanggal, pengirim/penerima, tahun).
"""
import re
from datetime import datetime
from typing import Dict, Optional

BULAN_ID = {
    'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
    'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
}


def extract_nomor_surat(text: str) -> Optional[str]:
    # Contoh pola umum nomor surat: 001/UG/PM/2026 atau 123/ABC/XI/2025
    m = re.search(r"\b[0-9]{1,4}/[A-Z0-9]+/(?:[A-Z]{2,}|[0-9]{2})/[0-9]{4}\b", text, re.IGNORECASE)
    return m.group(0) if m else None


def extract_perihal(text: str) -> Optional[str]:
    # Cari kata 'Perihal' atau 'Hal'
    m = re.search(r"(?:Perihal|Hal)\s*:\s*(.+)", text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_tanggal(text: str) -> Optional[datetime]:
    # Format: Jakarta, 12 Desember 2025 / 12 Desember 2025
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})", text, re.IGNORECASE)
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
    # Fallback: ada angka tahun saja
    y = re.search(r"\b(20\d{2})\b", text)
    if y:
        return datetime(int(y.group(1)), 1, 1)
    return None


def extract_pengirim_penerima(text: str) -> Dict[str, Optional[str]]:
    pengirim = None
    penerima = None
    # Heuristik sederhana
    m_to = re.search(r"Kepada\s+Yth\.?\s*(.+)", text, re.IGNORECASE)
    if m_to:
        penerima = m_to.group(1).strip()
    m_from = re.search(r"(?:Dari|Pengirim)\s*:\s*(.+)", text, re.IGNORECASE)
    if m_from:
        pengirim = m_from.group(1).strip()
    return {"pengirim": pengirim, "penerima": penerima}


def decide_tahun(tanggal: Optional[datetime], uploaded_at: datetime) -> int:
    if tanggal:
        return tanggal.year
    return uploaded_at.year
