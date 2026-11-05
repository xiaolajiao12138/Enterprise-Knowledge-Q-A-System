import os
import sys
from pathlib import Path

# 添加 backend 到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from init_db import init


if __name__ == "__main__":
    print("=" * 60)
    print("正在启动【企业内部知识问答平台】后端服务...")
    print("=" * 60)

    # 自动执行初始化数据库与账号
    try:
        init()
    except Exception as e:
        print(f"数据库初始化跳过或异常: {e}")

    print("后端服务启动中: http://127.0.0.1:8000")
    print("Swagger 接口文档: http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
