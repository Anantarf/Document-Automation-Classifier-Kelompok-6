
# app/services/ocr.py
"""
OCR untuk PDF scan menggunakan PyMuPDF (render) + pytesseract.
"""

import tempfile
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from app.config import settings

# Set path tesseract jika disediakan di .env
if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def ocr_pdf_to_text(path: str, dpi: int = 300) -> str:
    """
    Render setiap halaman PDF ke gambar dan lakukan OCR, gabungkan hasil per halaman.
    """
    text_chunks = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
                tmp.write(pix.tobytes("png"))
                tmp.flush()
                img = Image.open(tmp.name)
                txt = pytesseract.image_to_string(img, lang="ind")  # gunakan bahasa Indonesia jika tersedia
                text_chunks.append(txt)
    return "\n".join(text_chunks)
