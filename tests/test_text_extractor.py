import pytest
from pathlib import Path
from app.services.text_extraction import TextExtractor


def test_docx_extraction_writes_text(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    # Mock extract_text_from_docx
    def mock_docx(path):
        return "Isi dokumen DOCX untuk test"

    monkeypatch.setattr('app.services.text_extraction.extract_text_from_docx', mock_docx)

    extractor = TextExtractor()
    text_path, text_content, ocr_used = extractor.extract_text_and_save(
        content=b"fake-docx-content",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        base_dir=base_dir,
        temp_file_name="sample",
    )

    assert text_path is not None
    assert text_path.exists()
    assert "Isi dokumen DOCX" in text_content
    assert ocr_used is False


def test_pdf_parsing_no_ocr(tmp_path, monkeypatch):
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    # Mock parser to return text and is_scanned=False
    def mock_pdf(path):
        return ("Teks dari PDF yang dapat dibaca", False)

    monkeypatch.setattr('app.services.text_extraction.extract_text_from_pdf', mock_pdf)

    extractor = TextExtractor()
    text_path, text_content, ocr_used = extractor.extract_text_and_save(
        content=b"fake-pdf",
        mime_type="application/pdf",
        base_dir=base_dir,
        temp_file_name="p1",
    )

    assert text_content.startswith('Teks dari PDF')
    assert ocr_used is False


def test_pdf_scanned_uses_ocr_bytes(monkeypatch, tmp_path):
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    # Parser indicates scanned
    def mock_pdf(path):
        return ("", True)

    monkeypatch.setattr('app.services.text_extraction.extract_text_from_pdf', mock_pdf)

    # Patch TextExtractor._ocr_pdf_to_text_from_bytes to return sample OCR text
    def fake_ocr_bytes(self, content, dpi=200):
        return "Hasil OCR dari bytes"

    monkeypatch.setattr(TextExtractor, '_ocr_pdf_to_text_from_bytes', fake_ocr_bytes)

    extractor = TextExtractor()
    text_path, text_content, ocr_used = extractor.extract_text_and_save(
        content=b"fake-pdf",
        mime_type="application/pdf",
        base_dir=base_dir,
        temp_file_name="p_ocr",
    )

    assert text_content == "Hasil OCR dari bytes"
    assert ocr_used is True


def test_pdf_scanned_external_ocr(monkeypatch, tmp_path):
    base_dir = tmp_path / "base"
    base_dir.mkdir()

    def mock_pdf(path):
        return ("", True)

    monkeypatch.setattr('app.services.text_extraction.extract_text_from_pdf', mock_pdf)

    # Provide an external OCR function
    def external_ocr(path):
        return "Hasil OCR eksternal"

    extractor = TextExtractor(ocr_pdf_fn=external_ocr)
    text_path, text_content, ocr_used = extractor.extract_text_and_save(
        content=b"fake-pdf",
        mime_type="application/pdf",
        base_dir=base_dir,
        temp_file_name="p_ext",
    )

    assert text_content == "Hasil OCR eksternal"
    assert ocr_used is True
