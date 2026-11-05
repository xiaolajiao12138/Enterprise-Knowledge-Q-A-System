import time
import httpx
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.system_setting import SystemSetting, SystemLog
from app.schemas.setting import SystemConfigSchema, ModelTestRequest, LogResponse
from app.core.deps import get_current_admin
from app.core.logger import log_event, logger
from app.config import settings

router = APIRouter(prefix="/settings", tags=["系统配置与日志(管理员)"])


@router.get("", response_model=SystemConfigSchema, summary="获取系统所有配置项")
def get_system_config(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员获取系统当前运行参数"""
    records = db.query(SystemSetting).all()
    cfg_dict = {r.key: r.value for r in records}

    return SystemConfigSchema(
        llm_provider=cfg_dict.get("llm_provider", settings.DEFAULT_LLM_PROVIDER),
        llm_base_url=cfg_dict.get("llm_base_url", settings.DEFAULT_LLM_BASE_URL),
        llm_api_key=cfg_dict.get("llm_api_key", settings.DEFAULT_LLM_API_KEY),
        llm_model=cfg_dict.get("llm_model", settings.DEFAULT_LLM_MODEL),
        temperature=float(cfg_dict.get("temperature", settings.DEFAULT_TEMPERATURE)),
        top_p=float(cfg_dict.get("top_p", settings.DEFAULT_TOP_P)),
        top_k=int(cfg_dict.get("top_k", settings.DEFAULT_TOP_K)),
        embedding_provider=cfg_dict.get("embedding_provider", settings.DEFAULT_EMBEDDING_PROVIDER),
        embedding_base_url=cfg_dict.get("embedding_base_url", settings.DEFAULT_EMBEDDING_BASE_URL),
        embedding_api_key=cfg_dict.get("embedding_api_key", settings.DEFAULT_EMBEDDING_API_KEY),
        embedding_model=cfg_dict.get("embedding_model", settings.DEFAULT_EMBEDDING_MODEL),
        chunk_size=int(cfg_dict.get("chunk_size", settings.DEFAULT_CHUNK_SIZE)),
        chunk_overlap=int(cfg_dict.get("chunk_overlap", settings.DEFAULT_CHUNK_OVERLAP))
    )


@router.put("", summary="更新系统配置")
def update_system_config(
    new_cfg: SystemConfigSchema,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员更新系统大模型、向量模型与切片配置"""
    provider = new_cfg.llm_provider
    # 智能纠正：如果用户填了公网 API (https 或 v1) 且有 key，但下拉框依然选了 ollama，自动校正为 openai
    if provider == "ollama" and (
        new_cfg.llm_base_url.startswith("https://") or
        "v1" in new_cfg.llm_base_url or
        (new_cfg.llm_api_key and new_cfg.llm_api_key not in ["", "EMPTY"])
    ):
        provider = "openai"

    cfg_map = {
        "llm_provider": provider,
        "llm_base_url": new_cfg.llm_base_url,
        "llm_api_key": new_cfg.llm_api_key,
        "llm_model": new_cfg.llm_model,
        "temperature": str(new_cfg.temperature),
        "top_p": str(new_cfg.top_p),
        "top_k": str(new_cfg.top_k),
        "embedding_provider": new_cfg.embedding_provider,
        "embedding_base_url": new_cfg.embedding_base_url,
        "embedding_api_key": new_cfg.embedding_api_key,
        "embedding_model": new_cfg.embedding_model,
        "chunk_size": str(new_cfg.chunk_size),
        "chunk_overlap": str(new_cfg.chunk_overlap),
    }

    for key, val in cfg_map.items():
        record = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if record:
            record.value = val
        else:
            record = SystemSetting(key=key, value=val, description="用户更新配置")
            db.add(record)

    db.commit()
    log_event(db, "SYSTEM", "INFO", "管理员更新了系统参数配置", operator=admin.username)
    return {"message": "系统参数更新成功"}


@router.post("/test-model", summary="测试大模型接口连通性")
def test_model_connection(
    req: ModelTestRequest,
    admin: User = Depends(get_current_admin)
):
    """在线测试 Ollama 或 OpenAI 兼容端点的连通性与响应"""
    start_time = time.time()
    provider = req.provider.lower()
    base_url = req.base_url.rstrip("/")

    # 自动识别协议：如果是公网 https、含有 v1、或含有有效 key，走 OpenAI 协议
    is_openai_style = (
        provider != "ollama" or
        base_url.startswith("https://") or
        "v1" in base_url or
        (req.api_key and req.api_key not in ["", "EMPTY"])
    )

    try:
        if not is_openai_style and provider == "ollama":
            url = base_url + "/api/tags"
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    cost = round(time.time() - start_time, 2)
                    models = [m.get("name") for m in resp.json().get("models", [])]
                    return {
                        "status": "success",
                        "latency_seconds": cost,
                        "message": f"Ollama 连通成功！本地模型: {', '.join(models[:4]) or '暂无'}"
                    }
                else:
                    raise RuntimeError(f"Ollama 返回状态码 {resp.status_code}: {resp.text}")
        else:
            if not base_url.startswith("http"):
                base_url = "https://" + base_url

            if base_url.endswith("/chat/completions"):
                url = base_url
            elif base_url.endswith("/v1"):
                url = base_url + "/chat/completions"
            else:
                url = base_url + "/chat/completions"

            headers = {
                "Authorization": f"Bearer {req.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": req.model,
                "messages": [{"role": "user", "content": "你好"}],
                "max_tokens": 10
            }
            with httpx.Client(timeout=20.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    cost = round(time.time() - start_time, 2)
                    return {
                        "status": "success",
                        "latency_seconds": cost,
                        "message": f"大模型 API 连通成功！响应耗时: {cost}s (模型: {req.model})"
                    }
                else:
                    raise RuntimeError(f"API 响应失败 HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        return {
            "status": "error",
            "message": f"连接失败: {str(e)}"
        }


@router.get("/logs", summary="分页获取系统与文档运行日志")
def list_logs(
    module: Optional[str] = Query(None, description="模块筛选: AUTH, DOC, CHAT, SYSTEM"),
    level: Optional[str] = Query(None, description="级别筛选: INFO, WARNING, ERROR"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员查看系统运行日志与文档处理日志"""
    query = db.query(SystemLog)
    if module:
        query = query.filter(SystemLog.module == module.upper())
    if level:
        query = query.filter(SystemLog.level == level.upper())

    total = query.count()
    items = (
        query.order_by(SystemLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": it.id,
                "module": it.module,
                "level": it.level,
                "message": it.message,
                "details": it.details,
                "operator": it.operator,
                "created_at": it.created_at
            }
            for it in items
        ]
    }
