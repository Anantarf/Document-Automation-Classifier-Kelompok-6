"""
scripts/test_ocr.py

Diagnostic script to exercise OCR + parser on a sample PDF.
Usage (PowerShell):
  .\.venv\Scripts\Activate.ps1
  python scripts/test_ocr.py

It prints: available OCR libs, Tesseract path, whether OCR was used, and a snippet of extracted text.
"""
from pathlib import Path
from datetime import datetime
import sys

# Ensure dotenv is loaded so settings reads current .env values
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

print("== OCR diagnostic test ==")

# Check availability
try:
    import pytesseract
    print("pytesseract: available")
except Exception as e:
    pytesseract = None
    print("pytesseract: NOT available ->", e)

try:
    import fitz
    print("PyMuPDF (fitz): available")
except Exception as e:
    fitz = None
    print("PyMuPDF (fitz): NOT available ->", e)

from app.config import settings
print('TESSERACT_CMD (settings):', repr(settings.TESSERACT_CMD))
print('Compatibility tesseract_cmd:', repr(getattr(settings, 'tesseract_cmd', None)))

def _main():
    # Target PDF (update path if needed)
    pdf_path = Path('storage/arsip_kelurahan/0/keluar/string/original.pdf')
    if not pdf_path.exists():
        print('ERROR: expected file not found:', pdf_path)
        return 2

    from app.services.text_extraction import extract_text_and_save

    print('\nRunning extract_text_and_save...')
    base_dir = Path('storage/tmp_ocr')
    base_dir.mkdir(parents=True, exist_ok=True)
    content = pdf_path.read_bytes()
    text_path, text_content, ocr_used = extract_text_and_save(content=content, mime_type='application/pdf', base_dir=base_dir)

    print('ocr_used:', ocr_used)
    print('text_path:', text_path)
    print('text length:', len(text_content))

    if text_content:
        print('\n-- text preview (first 800 chars) --')
        print(text_content[:800])
    else:
        print('\nNo text extracted. If OCR is not available, please install Tesseract + pytesseract (+ PyMuPDF).')

    # Run parsing on extracted text to show what metadata parser finds
    from app.services.metadata import parse_metadata
    meta = parse_metadata(text_content or '', pdf_path.name, uploaded_at=datetime.utcnow())
    print('\nparse_metadata result:')
    for k, v in meta.items():
        print(f'  {k}: {v}')

    print('\nDone.')


if __name__ == '__main__':
    import sys
    sys.exit(_main() or 0)
