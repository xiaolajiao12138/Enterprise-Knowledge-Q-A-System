import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api import auth, users, documents, chat, settings as sys_settings
from app.core.logger import logger

# 创建 FastAPI 实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="企业内部私有化 RAG 知识库问答平台 API 接口文档。支持文档上传解析、向量检索、防幻觉生成与严格权限控制。",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 配置跨域中间件 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源跨域访问，方便前后端分离调试
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    """请求耗时监控中间件"""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    # 静态或轮询不打过多日志
    if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi"):
        logger.info(f"{request.method} {request.url.path} 完成 - 状态码: {response.status_code} - 耗时: {duration:.3f}s")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常捕获，避免未处理异常导致服务崩溃并输出友好提示"""
    logger.error(f"全局未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"服务器内部错误: {str(exc)}"}
    )


# 注册 API 路由
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)
app.include_router(chat.router, prefix=api_prefix)
app.include_router(sys_settings.router, prefix=api_prefix)


@app.get("/", summary="系统服务健康状态检查")
def root():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs_url": "/docs"
    }
