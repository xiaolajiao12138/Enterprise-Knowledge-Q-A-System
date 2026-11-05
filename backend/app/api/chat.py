import io
import csv
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatMessageCreate, ChatMessageResponse, ChatSessionCreate,
    ChatSessionResponse, SourceItem
)
from app.core.deps import get_current_user
from app.core.logger import log_event
from app.services.rag_service import rag_service

router = APIRouter(prefix="/chat", tags=["问答对话模块"])


@router.get("/sessions", response_model=List[ChatSessionResponse], summary="获取当前用户的会话列表")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取登录用户所有的问答会话列表"""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        count = db.query(ChatMessage).filter(ChatMessage.session_id == s.id).count()
        s_dict = {
            "id": s.id,
            "user_id": s.user_id,
            "title": s.title,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "message_count": count
        }
        result.append(s_dict)
    return result


@router.post("/sessions", response_model=ChatSessionResponse, summary="新建对话会话")
def create_session(
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """新建问答会话窗口"""
    session = ChatSession(
        user_id=current_user.id,
        title=data.title or "新对话"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "message_count": 0
    }


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse, summary="重命名会话")
def rename_session(
    session_id: int,
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改会话名称"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    session.title = data.title or session.title
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}", summary="删除会话")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除指定会话及所有消息记录"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.delete(session)
    db.commit()
    return {"message": "会话已删除"}


@router.post("/sessions/{session_id}/clear", summary="清空当前会话消息")
def clear_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """清空当前会话内的全部问答历史"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.commit()
    return {"message": "会话消息已清空"}


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse], summary="获取会话消息历史")
def get_session_messages(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取指定会话的历史记录列表"""
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    result = []
    for m in messages:
        sources_list = None
        if m.sources:
            try:
                sources_list = json.loads(m.sources)
            except Exception:
                sources_list = []
        result.append({
            "id": m.id,
            "session_id": m.session_id,
            "role": m.role,
            "content": m.content,
            "sources": sources_list,
            "created_at": m.created_at
        })
    return result


@router.post("/ask", summary="发送问题并获取 RAG 回答与引用来源")
def ask_question(
    req: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    RAG 智能问答接口：
    1. 向量检索知识库切片
    2. 基于检索片段与多轮历史生成答案
    3. 返回答案与引用来源并持久化存储
    """
    # 1. 确认或创建会话
    session = None
    if req.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == req.session_id,
            ChatSession.user_id == current_user.id
        ).first()

    if not session:
        # 截取用户问题的前 15 个字作为会话标题
        title = req.content[:20].strip() or "新对话"
        session = ChatSession(user_id=current_user.id, title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
    elif session.title == "新对话":
        session.title = req.content[:20].strip() or "新对话"
        db.commit()

    # 2. 检索历史上下文（最近 6 条）
    history_records = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(6)
        .all()
    )
    chat_history = [{"role": h.role, "content": h.content} for h in history_records]

    # 3. 保存用户提问消息
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=req.content
    )
    db.add(user_msg)
    db.commit()

    # 4. 执行 RAG 问答推理
    rag_result = rag_service.answer_question(
        question=req.content,
        chat_history=chat_history
    )
    answer_text = rag_result.get("answer", "")
    sources = rag_result.get("sources", [])

    # 5. 保存助手回答消息
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_text,
        sources=json.dumps(sources, ensure_ascii=False) if sources else None
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    log_event(db, "CHAT", "INFO", f"用户提问: {req.content[:30]}...", operator=current_user.username)

    return {
        "session_id": session.id,
        "user_message": {
            "id": user_msg.id,
            "role": "user",
            "content": user_msg.content,
            "created_at": user_msg.created_at
        },
        "assistant_message": {
            "id": assistant_msg.id,
            "role": "assistant",
            "content": assistant_msg.content,
            "sources": sources,
            "created_at": assistant_msg.created_at
        }
    }


@router.get("/export", summary="导出用户所有问答历史记录为 CSV")
def export_chat_history(
    session_id: Optional[int] = Query(None, description="可选指定导出某个会话，为空则导出全部"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """导出问答历史为 CSV（带 UTF-8 BOM，防止 Excel 打开乱码）"""
    query = (
        db.query(ChatMessage, ChatSession.title)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.user_id == current_user.id)
    )
    if session_id:
        query = query.filter(ChatMessage.session_id == session_id)

    records = query.order_by(ChatMessage.created_at.asc()).all()

    output = io.StringIO()
    # 写入 UTF-8 BOM
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["会话标题", "角色", "内容", "引用来源", "时间"])

    for msg, title in records:
        sources_desc = ""
        if msg.sources:
            try:
                src_list = json.loads(msg.sources)
                names = [s.get("filename", "") for s in src_list if s.get("filename")]
                sources_desc = " | ".join(set(names))
            except Exception:
                sources_desc = msg.sources

        writer.writerow([
            title,
            "用户" if msg.role == "user" else "知识库助手",
            msg.content,
            sources_desc,
            msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else ""
        ])

    output.seek(0)
    filename = f"chat_history_{current_user.username}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
