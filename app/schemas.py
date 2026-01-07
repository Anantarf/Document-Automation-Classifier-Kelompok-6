
# app/schemas.py
"""
Skema Pydantic untuk request/response API.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

class DocumentCreate(BaseModel):
    jenis: str = Field(example='surat_masuk')
    tahun: int
    nomor_surat: Optional[str] = None
    perihal: Optional[str] = None
    tanggal_surat: Optional[date] = None
    uploaded_by: Optional[str] = None

class DocumentRead(BaseModel):
    id: int
    file_name: str
    stored_path: str
    jenis: str
    tahun: int
    nomor_surat: Optional[str]
    perihal: Optional[str]
    tanggal_surat: Optional[date]
    confidence: Optional[float]
    status: str
    uploaded_by: Optional[str]
    uploaded_at: datetime

    class Config:
        from_attributes = True

class SearchQuery(BaseModel):
    tahun: Optional[int] = None
    jenis: Optional[str] = None
    nomor_surat: Optional[str] = None
    perihal: Optional[str] = None
