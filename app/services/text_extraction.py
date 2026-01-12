
# app/services/text_extraction.py
"""
Bridge untuk ekstraksi teks yang memanfaatkan parser buatan kamu:
- DOCX: app.services.parser_docx.extract_text_from_docx(path)
- PDF:  app.services.parser_pdf.extract_text_from_pdf(path) -> (text, is_scanned)
- OCR (opsional) untuk PDF scan jika TESSERACT_CMD di .env diisi.

Perubahan: diperkenalkan `TextExtractor` service class agar strategi ekstraksi dapat di-mock
atau di-inject untuk testing/konfigurasi. Sebuah wrapper `extract_text_and_save` tetap
tersedia untuk kompatibilitas.
"""

from pathlib import Path
from typing import Optional, Tuple, Callable
import io
import json

from app.config import settings
from app.constants import PDF2IMAGE_DPI, TMP_UPLOAD_NAME, TESSERACT_LANG

# Import parser buatan kamu
from app.services.parser_docx import extract_text_from_docx
from app.services.parser_pdf import extract_text_from_pdf

# OCR (opsional)
try:
    import pytesseract
    from pdf2image import convert_from_path, convert_from_bytes
except Exception:
    pytesseract = None
    convert_from_path = None
    convert_from_bytes = None


class TextExtractor:
    """Service class that encapsulates text extraction strategy for DOCX/PDF and OCR.

    It accepts optional injectable dependencies for easier testing/mocking.
    """

    def __init__(
        self,
        tesseract_cmd: Optional[Path] = None,
        pytesseract_mod=None,
        convert_from_bytes_fn: Callable | None = None,
        ocr_pdf_fn: Callable | None = None,
    ) -> None:
        self.tesseract_cmd = tesseract_cmd or (Path(settings.TESSERACT_CMD) if settings.TESSERACT_CMD else None)
        self.pytesseract = pytesseract_mod if pytesseract_mod is not None else pytesseract
        self.convert_from_bytes = convert_from_bytes_fn if convert_from_bytes_fn is not None else convert_from_bytes
        self.external_ocr_pdf = ocr_pdf_fn  # function(path) -> text (string)

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    def _ocr_pdf_to_text_from_bytes(self, content: bytes, dpi: int = PDF2IMAGE_DPI) -> str:
        """Attempt OCR from PDF bytes (pdf2image + pytesseract).

        Returns extracted text or empty string if not available.
        """
        if not (self.tesseract_cmd and self.pytesseract and self.convert_from_bytes):
            return ""
        
        try:
            try:
                self.pytesseract.pytesseract.tesseract_cmd = str(self.tesseract_cmd)
            except Exception:
                # If assignment fails, ignore and let pytesseract use defaults
                pass

            pages = self.convert_from_bytes(content, dpi=dpi)
            lines = []
            for img in pages:
                try:
                    t = self.pytesseract.image_to_string(img, lang=TESSERACT_LANG)
                except Exception:
                    t = self.pytesseract.image_to_string(img)
                lines.append(t)
            return "\n".join(lines).strip()
        except Exception as e:
            # Handle missing Poppler or other OCR errors gracefully
            import logging
            log = logging.getLogger(__name__)
            log.warning(f"OCR failed (Poppler/Tesseract might not be installed): {e}")
            return ""

    def extract_text_and_save(
        self,
        content: bytes,
        mime_type: str,
        base_dir: Path,
        temp_file_name: Optional[str] = None,
    ) -> Tuple[Optional[Path], str, bool]:
        """Main entry: save temporary upload, parse, try OCR fallback and write text.txt.

        Returns: (text_path, text_content, ocr_used)
        """
        text_content = ""
        ocr_used = False

        # Simpan sementara untuk parser kamu (karena butuh path)
        temp_dir: Path = settings.TEMP_UPLOAD_PATH
        temp_dir.mkdir(parents=True, exist_ok=True)
        name = temp_file_name or TMP_UPLOAD_NAME
        # Tentukan ekstensi sederhana dari MIME
        ext = ".pdf" if mime_type == "application/pdf" else ".docx"
        tmp_path = temp_dir / f"{name}{ext}"
        tmp_path.write_bytes(content)

        if mime_type == "application/pdf":
            # Pakai parser_pdf
            text, is_scanned = extract_text_from_pdf(tmp_path.as_posix())
            text_content = (text or "").strip()

            # OCR fallback jika scan dan OCR aktif/tersedia
            if is_scanned and not text_content:
                import logging
                log = logging.getLogger(__name__)
                log.info("PDF is scanned/image-only, attempting OCR...")
                
                # 1) coba OCR dari bytes (pdf2image + pytesseract) bila tersedia
                ocr_text = self._ocr_pdf_to_text_from_bytes(content)
                
                if ocr_text:
                    log.info(f"OCR successful: extracted {len(ocr_text)} characters")

                # 2) fallback ke PyMuPDF-based OCR (disk-based) jika in-memory OCR tidak tersedia
                if not ocr_text and self.external_ocr_pdf is not None:
                    try:
                        ocr_text = self.external_ocr_pdf(tmp_path.as_posix())
                    except Exception:
                        ocr_text = ""
                elif not ocr_text:
                    try:
                        # lazy import to avoid hard dependency
                        from app.services.ocr import ocr_pdf_to_text

                        ocr_text = ocr_pdf_to_text(tmp_path.as_posix())
                    except Exception:
                        ocr_text = ""

                if ocr_text:
                    text_content = ocr_text
                    ocr_used = True
                else:
                    log.warning("OCR returned no text. Install Poppler for better OCR support.")

        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # Pakai parser_docx
            text_content = (extract_text_from_docx(tmp_path.as_posix()) or "").strip()

        # Tulis text.txt jika ada
        text_path = None
        if text_content:
            from app.constants import TEXT_FILENAME
            text_path = base_dir / TEXT_FILENAME
            self._write_text(text_path, text_content)

        # Bersihkan file temp (best-effort)
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

        return text_path, text_content, ocr_used


# Backwards-compatible convenience function
_default_extractor = TextExtractor()


def extract_text_and_save(
    content: bytes,
    mime_type: str,
    base_dir: Path,
    temp_file_name: Optional[str] = None,
) -> Tuple[Optional[Path], str, bool]:
    return _default_extractor.extract_text_and_save(content=content, mime_type=mime_type, base_dir=base_dir, temp_file_name=temp_file_name)

