from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None
    mode: str = Field(default="text", pattern="^(text|voice)$")
    use_knowledge: bool = True


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    mode: str
    tools_used: list
    sources: list
    created_at: datetime


class ChatOut(BaseModel):
    conversation_id: str
    reply: MessageOut


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class RenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
