# app/services/classifier.py
"""
Klasifikasi dokumen: surat_masuk vs surat_keluar.
Support ML model (jika tersedia) atau fallback ke rule-based.
"""

import logging
import re
from typing import Tuple
from pathlib import Path

log = logging.getLogger(__name__)

# Try to load ML model if available
ML_MODEL = None
try:
    import joblib
    model_path = Path(__file__).parent.parent.parent / "data" / "classifier_model.pkl"
    if model_path.exists():
        ML_MODEL = joblib.load(model_path)
        log.info(f"✅ ML classifier loaded from {model_path}")
except Exception as e:
    log.warning(f"⚠️  ML model not available, using rule-based: {e}")

# Rule-based fallback keywords
KEYWORDS_KELUAR = [
    "kepada yth", "kepada yang terhormat", "yang terhormat", "di tempat",
    "surat keputusan", "surat tugas", "surat perintah"
]
KEYWORDS_MASUK = [
    "dari", "pengirim", "diterima", "stempel masuk", "permohonan", "undangan"
]

# Pola internal instansi (indikasi surat keluar)
INTERNAL_PATTERNS = [
    r"\bKelurahan\s+Pela\s+Mampang\b", 
    r"\bKecamatan\s+Mampang\s+Prapatan\b",
    r"\bLurah\s+Pela\s+Mampang\b"
]


def classify_ml(text: str) -> Tuple[str, float]:
    """
    Classify using ML model.
    Returns: (jenis, confidence)
    """
    try:
        prediction = ML_MODEL.predict([text])[0]
        proba = ML_MODEL.predict_proba([text])[0]
        confidence = max(proba)
        
        # Convert to our format
        jenis = "keluar" if prediction == "keluar" else "masuk"
        
        return jenis, float(confidence)
    except Exception as e:
        log.error(f"ML classification error: {e}")
        return classify_rules(text)


def classify_rules(text: str) -> Tuple[str, float]:
    """
    Rule-based classification fallback.
    Returns: (jenis, confidence)
    """
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
            score_keluar += 2

    if score_keluar == score_masuk:
        # fallback berdasarkan struktur: jika ada 'kepada yth' → keluar
        if "kepada yth" in t or "kepada yang terhormat" in t:
            score_keluar += 0.5
        else:
            score_masuk += 0.5

    jenis = "keluar" if score_keluar > score_masuk else "masuk"
    total_score = score_keluar + score_masuk
    confidence = abs(score_keluar - score_masuk) / max(total_score, 1)
    confidence = min(0.95, 0.5 + confidence / 2)  # normalisasi 0.5-0.95
    
    return jenis, confidence


def classify(text: str) -> Tuple[str, float]:
    """
    Main classification function.
    Uses ML model if available, otherwise falls back to rules.
    
    Returns:
        (jenis, confidence) where jenis is 'masuk' or 'keluar'
    """
    if ML_MODEL is not None:
        return classify_ml(text)
    else:
        return classify_rules(text)
