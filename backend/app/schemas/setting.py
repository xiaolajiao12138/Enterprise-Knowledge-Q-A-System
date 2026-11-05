from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class SystemConfigSchema(BaseModel):
    # LLM 参数
    llm_provider: str = Field("ollama", description="ollama 或 openai")
    llm_base_url: str = Field("http://127.0.0.1:11434", description="模型 API 地址")
    llm_api_key: str = Field("EMPTY", description="API Key")
    llm_model: str = Field("qwen2:7b", description="模型标识")
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    top_p: float = Field(0.8, ge=0.0, le=1.0)
    top_k: int = Field(4, ge=1, le=20, description="知识库检索 Top N")

    # 向量模型参数
    embedding_provider: str = Field("ollama", description="ollama 或 openai")
    embedding_base_url: str = Field("http://127.0.0.1:11434")
    embedding_api_key: str = Field("EMPTY")
    embedding_model: str = Field("nomic-embed-text")

    # 切片参数
    chunk_size: int = Field(500, ge=100, le=4000, description="分片大小")
    chunk_overlap: int = Field(50, ge=0, le=1000, description="重叠大小")


class ModelTestRequest(BaseModel):
    provider: str
    base_url: str
    api_key: Optional[str] = "EMPTY"
    model: str


class LogQueryRequest(BaseModel):
    module: Optional[str] = None
    level: Optional[str] = None
    page: int = 1
    page_size: int = 20


class LogResponse(BaseModel):
    id: int
    module: str
    level: str
    message: str
    details: Optional[str] = None
    operator: str
    created_at: datetime

    class Config:
        from_attributes = True
