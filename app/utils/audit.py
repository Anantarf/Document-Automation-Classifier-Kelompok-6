
# app/utils/audit.py
"""
Audit log util untuk mencatat aktivitas penting:
- upload | upload_duplicate | override | delete | export | error
"""

from sqlalchemy.orm import Session
from app.models import AuditLog


def log(session: Session, actor: str | None, action: str, doc_id: int | None, detail: str | None = None) -> None:
    entry = AuditLog(actor=actor, action=action, doc_id=doc_id, detail=detail)
    session.add(entry)
    session.commit()
