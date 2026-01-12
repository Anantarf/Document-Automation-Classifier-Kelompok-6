
# app/models.py
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey

# Definisikan Base DI SINI (jangan impor dari app.database)
Base = declarative_base()

# --- Skema contoh; sesuaikan jika kamu punya field lain ---

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)

    tahun = Column(Integer, index=True)
    jenis = Column(String(20), index=True)        # 'masuk' | 'keluar'
    # Keep DB column name as 'nomor' but expose it as `nomor_surat` on the model
    nomor_surat = Column("nomor", String(255), index=True)
    perihal = Column(String(255), index=True)

    tanggal_surat = Column(String(20), nullable=True)

    # Backwards-compatible attribute accessors for code that still uses `doc.nomor`
    @property
    def nomor(self) -> str | None:
        return self.nomor_surat

    @nomor.setter
    def nomor(self, value: str | None) -> None:
        self.nomor_surat = value
    pengirim = Column(String(255), nullable=True)
    penerima = Column(String(255), nullable=True)

    stored_path = Column(Text, nullable=False)
    metadata_path = Column(Text, nullable=False)

    uploaded_at = Column(DateTime, index=True)
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(100), index=True, nullable=True)
    ocr_enabled = Column(Boolean, default=False)


class OCRText(Base):
    __tablename__ = "ocr_texts"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    text_path = Column(Text, nullable=False)
    created_at = Column(DateTime, index=True)



class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)   # 'info' | 'error' dsb.
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, index=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="staf") # admin | staf
