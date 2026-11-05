import logging
import sys
from datetime import datetime

# 配置控制台输出格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("rag_system")


def log_event(db, module: str, level: str, message: str, details: str = None, operator: str = "system"):
    """
    记录业务日志到数据库系统日志表 (SystemLog)，以便前端管理页面查询
    """
    try:
        from app.models.system_setting import SystemLog
        log_entry = SystemLog(
            module=module,
            level=level.upper(),
            message=message,
            details=details,
            operator=operator,
            created_at=datetime.now()
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"写入系统日志失败: {e}")
