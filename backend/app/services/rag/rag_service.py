import hashlib
import io
import math
import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.entities import Document, DocumentChunk, User

HASH_DIMENSIONS = 512
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 4
ALLOWED_TYPES = {"pdf", "txt", "docx"}


def extract_text(file_type: str, data: bytes) -> str:
    if file_type == "txt":
        return data.decode("utf-8", errors="ignore")
    if file_type == "pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if file_type == "docx":
        from docx import Document as DocxDocument

        document = DocxDocument(io.BytesIO(data))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Unsupported file type")


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def hash_embedding(text: str) -> list[float]:
    vector = [0.0] * HASH_DIMENSIONS
    for token in re.findall(r"\w+", text.lower()):
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % HASH_DIMENSIONS
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def embed_texts(texts: list[str]) -> tuple[list[list[float]], str]:
    settings = get_settings()
    if settings.llm_api_key:
        try:
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/embeddings",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.embedding_model, "input": texts},
                timeout=60,
            )
            response.raise_for_status()
            rows = sorted(response.json()["data"], key=lambda item: item["index"])
            return [row["embedding"] for row in rows], "provider"
        except (httpx.HTTPError, KeyError, ValueError):
            pass
    return [hash_embedding(text) for text in texts], "local"


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def index_document(db: Session, document: Document, data: bytes) -> None:
    try:
        text = clean_text(extract_text(document.file_type, data))
        if not text:
            raise ValueError("No readable text found in the file")
        pieces = chunk_text(text)
        vectors, _ = embed_texts(pieces)
        for position, (piece, vector) in enumerate(zip(pieces, vectors)):
            db.add(DocumentChunk(document_id=document.id, chunk_index=position, content=piece, embedding=vector))
        document.chunk_count = len(pieces)
        document.status = "completed"
        document.error = None
    except Exception as exc:
        document.status = "failed"
        document.error = str(exc)[:500]
    db.commit()


def search(db: Session, user: User, query: str, top_k: int = TOP_K) -> list[dict]:
    rows = db.execute(
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.user_id == user.id, Document.status == "completed")
    ).all()
    if not rows:
        return []
    vectors, kind = embed_texts([query])
    query_vector = vectors[0]
    threshold = 0.3 if kind == "provider" else 0.12
    scored = []
    for chunk, document in rows:
        score = cosine(query_vector, chunk.embedding)
        if score >= threshold:
            scored.append(
                {
                    "document_id": document.id,
                    "source": document.name,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "score": round(score, 4),
                }
            )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]
