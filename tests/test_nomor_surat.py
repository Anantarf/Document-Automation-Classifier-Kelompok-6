from datetime import datetime
import csv
from io import StringIO
import asyncio

from app.database import SessionLocal
from app.models import Document

from app.services import text_extraction as te_mod
from app.services import metadata as metadata_mod
from app.routers.search import search_documents
from app.routers.export import export_csv
from app.routers.upload import upload_document


def _create_doc(session, nomor_surat: str, tahun: int = 2025, jenis: str = "keluar") -> Document:
    d = Document(
        tahun=tahun,
        jenis=jenis,
        nomor_surat=nomor_surat,
        perihal="test",
        tanggal_surat=None,
        pengirim=None,
        penerima=None,
        stored_path="/tmp/original.pdf",
        metadata_path="/tmp/metadata.json",
        uploaded_at=datetime.utcnow(),
        mime_type="application/pdf",
        file_hash=None,
        ocr_enabled=False,
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def test_search_and_export_nomor_surat():
    session = SessionLocal()
    try:
        doc = _create_doc(session, "TEST-001", tahun=2025, jenis="keluar")

        # Call search_documents directly
        rows = search_documents(
            tahun=doc.tahun, jenis=doc.jenis, nomor=None, nomor_surat=doc.nomor_surat,
            perihal=None, limit=100, offset=0, db=session
        )
        assert isinstance(rows, list) and len(rows) >= 1
        assert any(getattr(r, "nomor_surat") == doc.nomor_surat for r in rows)

        # Call export_csv directly and read StreamingResponse content
        resp = export_csv(tahun=doc.tahun, jenis=doc.jenis, nomor=None, perihal=None, limit=10000, db=session)
        # Try synchronous iteration first
        body = b""
        it = getattr(resp, "body_iterator", None)
        if it is None:
            raise AssertionError("no body iterator on StreamingResponse")
        try:
            body = b"".join(it)
        except TypeError:
            # async iterator
            async def read_async(it):
                out = b""
                async for chunk in it:
                    out += chunk
                return out
            body = asyncio.get_event_loop().run_until_complete(read_async(it))

        csv_text = body.decode("utf-8")
        assert "nomor_surat" in csv_text.splitlines()[0]
        assert doc.nomor_surat in csv_text

    finally:
        # cleanup
        session.delete(doc)
        session.commit()
        session.close()


def test_upload_returns_both_nomor_keys(monkeypatch, tmp_path):
    # Mock text extraction to return OCRed text and mark ocr_used True
    # Note: upload router imports local references, so patch them there
    import app.routers.upload as upload_mod
    monkeypatch.setattr(upload_mod, "extract_text_and_save", lambda content, mime_type, base_dir: (None, "Nomor: XYZ/123", True))
    monkeypatch.setattr(upload_mod, "parse_metadata", lambda text, filename, uploaded_at=None: {"nomor": "XYZ/123", "perihal": "upload test", "tahun": 2025, "jenis": "keluar"})
    # Also patch service modules for completeness
    monkeypatch.setattr(te_mod, "extract_text_and_save", lambda content, mime_type, base_dir: (None, "Nomor: XYZ/123", True))
    monkeypatch.setattr(metadata_mod, "parse_metadata", lambda text, filename, uploaded_at=None: {"nomor": "XYZ/123", "perihal": "upload test", "tahun": 2025, "jenis": "keluar"})
    # Build a dummy UploadFile-like object
    class DummyUploadFile:
        def __init__(self, filename, content_type, content_bytes):
            self.filename = filename
            self.content_type = content_type
            self._content = content_bytes

        async def read(self):
            return self._content

    session = SessionLocal()
    try:
        # Call upload_document directly
        import uuid
        unique = b"%PDF-1.4 test " + uuid.uuid4().hex.encode()
        dummy = DummyUploadFile("test.pdf", "application/pdf", unique)
        result = asyncio.get_event_loop().run_until_complete(
            upload_document(
                file=dummy, tahun=None, jenis=None, nomor=None, perihal=None,
                tanggal_surat=None, pengirim=None, penerima=None, db=session
            )
        )

        # ensure both keys present in returned dict
        assert isinstance(result, dict)
        assert "nomor" in result and "nomor_surat" in result
        assert result["nomor"] == "XYZ/123"
        assert result["nomor_surat"] == "XYZ/123"

        # verify DB record exists and has nomor_surat set
        d = session.query(Document).filter(Document.nomor_surat == "XYZ/123").first()
        assert d is not None

        # cleanup
        if d:
            session.delete(d)
            session.commit()
    finally:
        session.close()
