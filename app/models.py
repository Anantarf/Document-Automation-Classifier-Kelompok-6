
# app/models.py
"""
Model SQLAlchemy: documents, ocr_text, audit_log.
Mencakup metadata arsip dokumen, teks hasil OCR/parsing, dan audit aktivitas.
"""

from datetime import datetime, date
from sqlalchemy import (
    String, Text, Date, DateTime, Float, Integer,
    ForeignKey, CheckConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    # Identitas & file
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Klasifikasi inti
    jenis: Mapped[str] = mapped_column(String(20), nullable=False)  # 'surat_masuk' | 'surat_keluar'
    tahun: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata tambahan
    nomor_surat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    perihal: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tanggal_surat: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Status proses
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="processed")  # processed|needs_review|error

    # Audit dasar
    uploaded_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relasi ke teks OCR/parsing (one-to-one)
    ocr_text: Mapped["OCRText"] = relationship(
        "OCRText",
        uselist=False,
        back_populates="document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("jenis IN ('surat_masuk','surat_keluar')", name="chk_jenis"),
        Index("idx_documents_tahun_jenis", "tahun", "jenis"),
        Index("idx_documents_nomor_surat", "nomor_surat"),
        Index("idx_documents_perihal", "perihal"),
    )


class OCRText(Base):
    __tablename__ = "ocr_text"

    # Primary key mengikuti doc_id (one-to-one)
    doc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_time: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    # Relasi balik ke Document
    document: Mapped[Document] = relationship("Document", back_populates="ocr_text")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(50))  # upload|override|delete|export|error
    doc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_auditlog_action", "action"),
        Index("idx_auditlog_doc", "doc_id"),
        Index("idx_auditlog_created_at", "created_at"),
    )
