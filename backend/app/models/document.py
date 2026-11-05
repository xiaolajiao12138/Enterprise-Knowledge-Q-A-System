from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="服务端本地存储路径")
    file_size = Column(Integer, default=0, comment="文件大小(字节)")
    file_type = Column(String(20), nullable=False, comment="文件类型扩展名(.pdf, .docx等)")
    status = Column(String(20), default="processing", comment="状态: processing, completed, failed")
    error_msg = Column(Text, nullable=True, comment="解析失败原因")
    chunk_count = Column(Integer, default=0, comment="切片总数量")
    created_at = Column(DateTime, default=datetime.now, comment="上传时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
