
# app/services/classifier.py
"""
Klasifikasi rule-based: surat_masuk vs surat_keluar.
"""

import re
from typing import Tuple

# Aturan sederhana berbasis kata kunci & pola
KEYWORDS_KELUAR = [
    "kepada yth", "kepada yang terhormat", "yang terhormat", "di",
]
KEYWORDS_MASUK = [
    "dari", "pengirim", "diterima", "stempel masuk"
]

# Pola internal instansi (indikasi surat keluar)
INTERNAL_PATTERNS = [r"\bKelurahan\s+Pela\s+Mampang\b", r"\bKecamatan\s+Mampang\s+Prapatan\b"]


def classify(text: str) -> Tuple[str, float]:
    t = text.lower()
    score_keluar = 0
    score_masuk = 0

    for kw in KEYWORDS_KELUAR:
        if kw in t:
            score_keluar += 1
    for kw in KEYWORDS_MASUK:
        if kw in t:
            score_masuk += 1

    # Pola internal → indikasi surat keluar
    for pat in INTERNAL_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            score_keluar += 1

    if score_keluar == score_masuk:
        # fallback berdasarkan struktur: jika ada 'kepada yth' → keluar
        if "kepada yth" in t:
            score_keluar += 0.1
        else:
            score_masuk += 0.1

    jenis = "surat_keluar" if score_keluar > score_masuk else "surat_masuk"
    confidence = abs(score_keluar - score_masuk) / max(score_keluar + score_masuk, 1)
    confidence = min(0.99, 0.5 + confidence / 2)  # normalisasi sederhana
    return jenis, confidence
