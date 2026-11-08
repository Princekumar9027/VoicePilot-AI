from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.entities import Conversation, Document, Message, ToolCall, User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation_ids = select(Conversation.id).where(Conversation.user_id == user.id)
    messages = db.scalar(select(func.count(Message.id)).where(Message.conversation_id.in_(conversation_ids))) or 0
    voice = db.scalar(
        select(func.count(Message.id)).where(Message.conversation_id.in_(conversation_ids), Message.mode == "voice", Message.role == "user")
    ) or 0
    return {
        "conversations": db.scalar(select(func.count(Conversation.id)).where(Conversation.user_id == user.id)) or 0,
        "messages": messages,
        "voice_messages": voice,
        "documents": db.scalar(select(func.count(Document.id)).where(Document.user_id == user.id)) or 0,
        "tool_calls": db.scalar(select(func.count(ToolCall.id)).where(ToolCall.user_id == user.id)) or 0,
    }


@router.get("/usage")
def usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=6)
    days = [(since + timedelta(days=i)).date() for i in range(7)]
    conversation_ids = select(Conversation.id).where(Conversation.user_id == user.id)
    messages = db.scalars(
        select(Message.created_at).where(Message.conversation_id.in_(conversation_ids), Message.created_at >= since.replace(hour=0, minute=0, second=0))
    ).all()
    tools = db.execute(
        select(ToolCall.tool_name, func.count(ToolCall.id)).where(ToolCall.user_id == user.id).group_by(ToolCall.tool_name)
    ).all()
    counts = {day: 0 for day in days}
    for created in messages:
        if created.date() in counts:
            counts[created.date()] += 1
    return {
        "messages_per_day": [{"date": day.isoformat(), "count": counts[day]} for day in days],
        "tool_usage": [{"tool": name, "count": count} for name, count in tools],
    }
