#!/bin/bash
# ==============================================================================
# 企业内部知识问答平台（RAG）Linux 服务器一键自动化部署脚本
# ==============================================================================

set -e

echo "======================================================================"
echo "          正在开始部署【企业内部知识问答平台 (RAG)】..."
echo "======================================================================"

# 1. 检查 Docker 环境
if ! command -v docker &> /dev/null; then
    echo ">> 未检测到 Docker，正在尝试自动安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    systemctl daemon-reload
    systemctl restart docker
    systemctl enable docker
    echo ">> Docker 安装成功！"
fi

# 2. 检查 Docker Compose
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo ">> 正在安装 Docker Compose 插件..."
    apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
fi

# 3. 确保数据目录权限
mkdir -p backend/data/uploads backend/data/chroma_db backend/data/demo_docs
chmod -R 777 backend/data

# 4. 构建并启动容器
echo ">> 正在构建并启动 Docker 容器组 (前后端 + Nginx)..."
docker compose down || true
docker compose build
docker compose up -d

echo "======================================================================"
echo "【恭喜】企业内部知识问答平台已成功部署上线！"
echo ""
echo "系统访问地址: http://<您的服务器公网IP>"
echo "API 接口文档: http://<您的服务器公网IP>:8000/docs"
echo ""
echo "默认体验账号:"
echo "  - 系统管理员: admin / admin123"
echo "  - 普通员工:   staff / staff123"
echo "======================================================================"
