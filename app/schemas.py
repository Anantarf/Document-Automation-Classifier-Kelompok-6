
# app/schemas.py
"""
Skema Pydantic untuk request/response API.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DocumentCreate(BaseModel):
    jenis: str = Field(example='surat_masuk')
    tahun: int
    nomor_surat: Optional[str] = None
    perihal: Optional[str] = None
    uploaded_by: Optional[str] = None

class DocumentRead(BaseModel):
    """Match actual Document model fields"""
    id: int
    tahun: Optional[int] = None  # Allow None for invalid docs
    jenis: str
    nomor_surat: Optional[str] = None
    perihal: Optional[str] = None
    tanggal_surat: Optional[str] = None
    bulan: Optional[str] = None
    pengirim: Optional[str] = None
    penerima: Optional[str] = None
    stored_path: str
    metadata_path: str
    uploaded_at: datetime
    mime_type: str
    file_hash: Optional[str] = None
    ocr_enabled: bool = False

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    tahun: Optional[int] = None
    jenis: Optional[str] = None
    nomor_surat: Optional[str] = None
    perihal: Optional[str] = None
