
# app/services/ocr.py
"""
OCR untuk PDF scan menggunakan PyMuPDF (render) + pytesseract.
"""

import logging
import tempfile
from pathlib import Path
from app.config import settings

log = logging.getLogger(__name__)

# Optional OCR deps: import safely so module import won't fail when not installed
try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

# Set path tesseract jika disediakan di .env (gunakan nama setting yang benar)
if pytesseract and settings.TESSERACT_CMD:
    try:
        pytesseract.pytesseract.tesseract_cmd = str(settings.TESSERACT_CMD)
    except Exception:
        # ignore assignment errors; function will check pytesseract presence at runtime
        pass


from app.constants import DEFAULT_OCR_DPI, TESSERACT_LANG

def ocr_pdf_to_text(path: str, dpi: int = DEFAULT_OCR_DPI) -> str:
    """
    Render setiap halaman PDF ke gambar dan lakukan OCR, gabungkan hasil per halaman.

    Perbaikan:
    - Coba bahasa 'ind' lalu fallback ke default jika gagal
    - Konversi ke grayscale dan sederhana threshold bila perlu
    - Tangani error per-halaman agar OCR halaman lain tetap berjalan
    - Improved logging dan tempfile cleanup dengan context manager
    """
    text_chunks = []

    if not pytesseract:
        log.warning("pytesseract not available, OCR skipped")
        return ""

    with fitz.open(path) as doc:
        total_pages = doc.page_count
        log.info(f"Starting OCR on {path}: {total_pages} pages")
        for page_number, page in enumerate(doc, start=1):
            try:
                pix = page.get_pixmap(dpi=dpi)
            except Exception as e:
                log.warning(f"Failed to render page {page_number}: {e}")
                continue

            # Use TemporaryDirectory context manager for automatic cleanup
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_file = Path(tmp_dir) / f"page_{page_number}.png"
                    tmp_file.write_bytes(pix.tobytes("png"))

                    img = Image.open(tmp_file)
                    # Konversi ke grayscale untuk meningkatkan OCR pada gambar dokumen
                    img = img.convert("L")

                    # Coba OCR dengan bahasa Indonesia terlebih dahulu
                    try:
                        txt = pytesseract.image_to_string(img, lang=TESSERACT_LANG)
                    except Exception as e:
                        log.debug(f"Page {page_number} OCR with lang={TESSERACT_LANG} failed: {e}")
                        # Fallback tanpa spesifikasi bahasa
                        try:
                            txt = pytesseract.image_to_string(img)
                        except Exception as e:
                            log.error(f"Page {page_number} OCR default failed: {e}")
                            txt = ""

                    log.debug(f"Page {page_number} OCR extracted {len(txt or '')} chars")
                    text_chunks.append(txt or "")
            except Exception as e:
                # Jangan berhenti jika satu halaman gagal
                log.error(f"Page {page_number} processing failed: {e}", exc_info=True)
                text_chunks.append("")

    result = "\n".join([t for t in text_chunks if t and t.strip()])
    log.info(f"OCR completed: {len(result)} chars extracted from {path}")
    return result.strip()
