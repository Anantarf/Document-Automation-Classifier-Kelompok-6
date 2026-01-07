
# app/services/parser_pdf.py
"""
Ekstraksi teks dari PDF. Coba teks native; bila kosong, tandai sebagai scan.
"""

from typing import Tuple
from pdfminer.high_level import extract_text


def extract_text_from_pdf(path: str) -> Tuple[str, bool]:
    """
    Returns: (text, is_scanned)
    is_scanned True bila text kosong/nyaris kosong -> perlu OCR.
    """
    try:
        text = extract_text(path) or ""
    except Exception:
        text = ""
    is_scanned = (len(text.strip()) < 20)  # ambang sederhana
    return (text, is_scanned)
