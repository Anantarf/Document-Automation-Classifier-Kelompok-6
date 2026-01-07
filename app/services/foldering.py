
# app/services/foldering.py
"""
Menyimpan dokumen ke struktur folder per tahun/jenis dan menulis metadata.json.
"""
import os
import json
from typing import Dict, Optional
from app.utils.slugs import slugify


def target_dir(root: str, tahun: int, jenis: str, nomor_surat: Optional[str], perihal: Optional[str]) -> str:
    slug = slugify(perihal or "tanpa-perihal")
    nomor = (nomor_surat or "tanpa-nomor").replace("/", "_")
    return os.path.join(root, str(tahun), jenis, f"{nomor}_{slug}")


def write_metadata(dir_path: str, metadata: Dict):
    os.makedirs(dir_path, exist_ok=True)
    meta_path = os.path.join(dir_path, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    return meta_path
