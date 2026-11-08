from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.entities import Document, User
from app.services.rag import rag_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAGIC = {"pdf": b"%PDF", "docx": b"PK"}


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    file_type: str
    size_bytes: int
    status: str
    error: str | None
    chunk_count: int
    created_at: datetime


class SearchOut(BaseModel):
    matches: list[dict]


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    name = (file.filename or "document").strip()[:255]
    file_type = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if file_type not in rag_service.ALLOWED_TYPES:
        raise HTTPException(400, "Only PDF, TXT and DOCX files are supported")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, "The file is empty")
    if file_type in MAGIC and not data.startswith(MAGIC[file_type]):
        raise HTTPException(400, "File content does not match its extension")
    document = Document(user_id=user.id, name=name, file_type=file_type, size_bytes=len(data), status="processing")
    db.add(document)
    db.commit()
    rag_service.index_document(db, document, data)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())).all()


@router.get("/search", response_model=SearchOut)
def search_documents(q: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return SearchOut(matches=rag_service.search(db, user, q))


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(404, "Document not found")
    db.delete(document)
    db.commit()
