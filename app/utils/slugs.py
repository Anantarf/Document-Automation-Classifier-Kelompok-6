
# app/utils/slugs.py
"""
Slugify teks (perihal) untuk nama folder yang aman.
"""

import re


def slugify(text: str) -> str:
    text = text.strip().lower()
    # Hapus karakter non-alfanumerik kecuali spasi & tanda minus
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    # Ganti spasi beruntun dengan satu tanda minus
    text = re.sub(r"[\s-]+", "-", text)
    # Batasi panjang slug agar tidak berlebihan
    return text[:80]
