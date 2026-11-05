from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key = Column(String(100), unique=True, index=True, nullable=False, comment="配置键名")
    value = Column(Text, nullable=False, comment="配置值(支持 JSON 字符串)")
    description = Column(String(255), nullable=True, comment="配置说明")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="修改时间")


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    module = Column(String(50), nullable=False, index=True, comment="业务模块(AUTH/DOC/CHAT/SYSTEM)")
    level = Column(String(20), default="INFO", index=True, comment="日志级别(INFO/WARNING/ERROR)")
    message = Column(String(500), nullable=False, comment="简短消息")
    details = Column(Text, nullable=True, comment="详细错误或参数堆栈")
    operator = Column(String(50), default="system", comment="操作人用户名")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="产生时间")
