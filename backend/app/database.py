from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# 创建 SQLite 数据库引擎
# check_same_thread 设置为 False 允许跨线程共享会话（适用于 FastAPI 多线程任务）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 实体基类
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库会话并在请求结束后自动关闭"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
