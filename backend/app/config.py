import os
from pathlib import Path
from pydantic_settings import BaseSettings

# 后端基础路径
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"
DEMO_DIR = DATA_DIR / "demo_docs"

# 确保核心数据目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    PROJECT_NAME: str = "企业内部知识问答平台"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # 路径配置
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    CHROMA_DIR: Path = CHROMA_DIR
    DEMO_DIR: Path = DEMO_DIR

    # 安全与 JWT 配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "rag-enterprise-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 默认 24 小时过期

    # 数据库路径 (SQLite)
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'rag_system.db'}"

    # 文件上传限制 (MB)
    MAX_FILE_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx", ".txt", ".md"]

    # 知识库与切片默认配置
    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 50
    DEFAULT_TOP_K: int = 4

    # 大模型默认配置
    DEFAULT_LLM_PROVIDER: str = "ollama"  # ollama 或 openai
    DEFAULT_LLM_BASE_URL: str = "http://127.0.0.1:11434"
    DEFAULT_LLM_API_KEY: str = "EMPTY"
    DEFAULT_LLM_MODEL: str = "qwen2:7b"
    DEFAULT_TEMPERATURE: float = 0.1
    DEFAULT_TOP_P: float = 0.8

    # 向量模型默认配置
    DEFAULT_EMBEDDING_PROVIDER: str = "ollama"  # ollama 或 openai
    DEFAULT_EMBEDDING_BASE_URL: str = "http://127.0.0.1:11434"
    DEFAULT_EMBEDDING_API_KEY: str = "EMPTY"
    DEFAULT_EMBEDDING_MODEL: str = "nomic-embed-text"

    class Config:
        case_sensitive = True
        arbitrary_types_allowed = True


settings = Settings()
