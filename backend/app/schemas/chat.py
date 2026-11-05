from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    document_id: Optional[int] = None
    filename: str
    chunk_index: int
    content_preview: str
    score: Optional[float] = None


class ChatMessageCreate(BaseModel):
    session_id: Optional[int] = None
    content: str = Field(..., min_length=1, description="用户问题内容")


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    sources: Optional[List[SourceItem]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    title: Optional[str] = "新对话"


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True
