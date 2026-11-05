import json
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.document import Document
from app.models.chat import ChatSession, ChatMessage
from app.models.system_setting import SystemSetting, SystemLog
from app.core.security import get_password_hash
from app.config import settings


def init():
    print("[1/3] 正在创建数据库表结构...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("[2/3] 正在检查并初始化默认管理员与测试账号...")
        # 1. 默认管理员
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="admin",
                is_active=True
            )
            db.add(admin)
            print("  -> 创建默认管理员: admin / admin123")
        else:
            print("  -> 管理员 admin 已存在")

        # 2. 默认普通员工
        emp = db.query(User).filter(User.username == "staff").first()
        if not emp:
            emp = User(
                username="staff",
                password_hash=get_password_hash("staff123"),
                role="employee",
                is_active=True
            )
            db.add(emp)
            print("  -> 创建默认普通员工: staff / staff123")
        else:
            print("  -> 普通员工 staff 已存在")

        print("[3/3] 正在初始化默认系统配置项...")
        default_configs = {
            "llm_provider": settings.DEFAULT_LLM_PROVIDER,
            "llm_base_url": settings.DEFAULT_LLM_BASE_URL,
            "llm_api_key": settings.DEFAULT_LLM_API_KEY,
            "llm_model": settings.DEFAULT_LLM_MODEL,
            "temperature": str(settings.DEFAULT_TEMPERATURE),
            "top_p": str(settings.DEFAULT_TOP_P),
            "top_k": str(settings.DEFAULT_TOP_K),
            "embedding_provider": settings.DEFAULT_EMBEDDING_PROVIDER,
            "embedding_base_url": settings.DEFAULT_EMBEDDING_BASE_URL,
            "embedding_api_key": settings.DEFAULT_EMBEDDING_API_KEY,
            "embedding_model": settings.DEFAULT_EMBEDDING_MODEL,
            "chunk_size": str(settings.DEFAULT_CHUNK_SIZE),
            "chunk_overlap": str(settings.DEFAULT_CHUNK_OVERLAP)
        }

        for key, val in default_configs.items():
            setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
            if not setting:
                setting = SystemSetting(key=key, value=val, description=f"默认配置 {key}")
                db.add(setting)

        # 记录初始化系统日志
        init_log = SystemLog(
            module="SYSTEM",
            level="INFO",
            message="系统数据库及初始配置初始化完成",
            operator="system"
        )
        db.add(init_log)

        db.commit()
        print(">>> 数据库与账号初始化完成！")

    finally:
        db.close()


if __name__ == "__main__":
    init()
