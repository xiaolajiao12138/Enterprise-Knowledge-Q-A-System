from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    file_type: str
    status: str
    error_msg: Optional[str] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChromaStatsResponse(BaseModel):
    collection_name: str
    total_vectors: int
    status: str
