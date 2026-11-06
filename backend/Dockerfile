FROM python:3.12-slim

WORKDIR /app

# 替换为国内阿里云 Debian 镜像源，彻底解决境外 deb.debian.org 访问缓慢卡死问题
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true

# 设置国内时区环境变量
ENV TZ=Asia/Shanghai

# 仅安装轻量 curl 与时区 tzdata 工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并使用国内清华源高速安装 (均为预编译二进制 Wheel 包，无需现场编译)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制后端业务代码
COPY . /app/

# 确保持久化目录存在
RUN mkdir -p /app/data/uploads /app/data/chroma_db /app/data/demo_docs

EXPOSE 8000

# 启动入口：启动前自动初始化数据库
CMD ["sh", "-c", "python init_db.py && python run.py"]
