from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.agent import run_agent
from app.api.conversations import owned
from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.entities import Conversation, Message, User
from app.schemas.chat import ChatIn, ChatOut, MessageOut

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/chat", response_model=ChatOut)
def chat(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.conversation_id:
        conversation = owned(db, user, body.conversation_id)
    else:
        conversation = Conversation(user_id=user.id, title=body.message[:60], mode=body.mode)
        db.add(conversation)
        db.commit()
    history = list(conversation.messages)
    if not history and conversation.title == "New conversation":
        conversation.title = body.message[:60]
    db.add(Message(conversation_id=conversation.id, role="user", content=body.message, mode=body.mode))
    db.commit()
    result = run_agent(db, user, history, body.message, body.use_knowledge)
    reply = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["content"],
        mode=body.mode,
        tools_used=result["tools_used"],
        sources=result["sources"],
    )
    db.add(reply)
    conversation.mode = body.mode
    db.commit()
    return ChatOut(conversation_id=conversation.id, reply=MessageOut.model_validate(reply))
