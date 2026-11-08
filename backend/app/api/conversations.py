from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.entities import Conversation, User
from app.schemas.chat import ConversationDetail, ConversationOut, RenameIn

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def owned(db: Session, user: User, conversation_id: str) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return conversation


@router.post("", response_model=ConversationOut, status_code=201)
def create(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = Conversation(user_id=user.id)
    db.add(conversation)
    db.commit()
    return conversation


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    q: str | None = Query(default=None, max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if q:
        stmt = stmt.where(Conversation.title.ilike(f"%{q}%"))
    return db.scalars(stmt.order_by(Conversation.updated_at.desc())).all()


@router.get("/{conversation_id}", response_model=ConversationDetail)
def detail(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned(db, user, conversation_id)


@router.patch("/{conversation_id}", response_model=ConversationOut)
def rename(conversation_id: str, body: RenameIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = owned(db, user, conversation_id)
    conversation.title = body.title.strip()
    db.commit()
    return conversation


@router.delete("/{conversation_id}", status_code=204)
def delete(conversation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(owned(db, user, conversation_id))
    db.commit()
