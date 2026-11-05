FROM python:3.12-slim

WORKDIR /app

# 安装系统基础依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端代码
COPY . /app/

# 创建持久化数据目录
RUN mkdir -p /app/data/uploads /app/data/chroma_db /app/data/demo_docs

EXPOSE 8000

# 启动入口：启动前自动初始化数据库
CMD ["sh", "-c", "python init_db.py && python run.py"]
