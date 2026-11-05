import os
import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.schemas.document import DocumentResponse, ChromaStatsResponse
from app.core.deps import get_current_admin, get_current_user
from app.core.logger import log_event, logger
from app.config import settings, UPLOAD_DIR
from app.services.background_tasks import process_document_task
from app.services.vector_store import vector_service
from app.services.document_parser import DocumentParser

router = APIRouter(prefix="/documents", tags=["知识库文档管理(管理员)"])


@router.post("/upload", response_model=DocumentResponse, summary="上传文档并触发异步向量化")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    管理员上传企业文档 (PDF, DOCX, TXT, MD)
    大小限制: 最大 20MB
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式 [{ext}]，仅支持: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # 读取内容并检查大小
    contents = await file.read()
    file_size = len(contents)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超出限制，当前为 {file_size / (1024*1024):.2f}MB，最大允许 {settings.MAX_FILE_SIZE_MB}MB"
        )

    # 保存到上传目录
    safe_name = f"{Path(file.filename).stem}_{os.urandom(4).hex()}{ext}"
    dest_path = UPLOAD_DIR / safe_name
    with open(dest_path, "wb") as f:
        f.write(contents)

    # 写入数据库记录
    doc = Document(
        filename=file.filename,
        file_path=str(dest_path),
        file_size=file_size,
        file_type=ext,
        status="processing",
        chunk_count=0
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_event(db, "DOC", "INFO", f"上传文档: {file.filename} ({file_size} 字节)", operator=admin.username)

    # 提交异步后台解析与切片入库任务
    background_tasks.add_task(process_document_task, doc.id)

    return doc


@router.get("", response_model=List[DocumentResponse], summary="获取知识库文档列表")
def list_documents(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取所有知识库文档列表及其处理状态"""
    return db.query(Document).order_by(Document.id.desc()).all()


@router.get("/{document_id}/preview", summary="预览文档解析文本内容")
def preview_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """预览文档文本前 3000 个字符"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="本地文档文件已丢失")

    try:
        pages = DocumentParser.parse(doc.file_path)
        combined = "\n\n".join([f"--- 第 {p.get('page', 1)} 页/段 ---\n{p.get('text', '')}" for p in pages])
        preview_text = combined[:8000]
        return {
            "filename": doc.filename,
            "preview_text": preview_text,
            "total_chars": len(combined),
            "total_pages": len(pages)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览解析失败: {str(e)}")


@router.get("/{document_id}/download", summary="下载知识库原始文档")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """下载或在线读取原始文档二进制文件"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="文档文件不存在")

    return FileResponse(
        path=doc.file_path,
        filename=doc.filename
    )


@router.delete("/{document_id}", summary="删除知识库文档")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """删除知识库文档、清理其在向量库中的向量并删除物理文件"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 1. 从 Chroma 移除向量
    vector_service.delete_by_document_id(doc.id)

    # 2. 删除本地物理文件
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"删除物理文件异常: {e}")

    filename = doc.filename
    db.delete(doc)
    db.commit()

    log_event(db, "DOC", "INFO", f"删除知识库文档: {filename} (ID={document_id})", operator=admin.username)
    return {"message": f"文档 [{filename}] 已成功删除，相关向量已移除"}


@router.post("/{document_id}/reindex", summary="重新向量化文档")
def reindex_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """当切片配置修改或解析失败时，触发重新解析与切片向量化"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=400, detail="本地源文件已不存在，无法重新向量化")

    doc.status = "processing"
    doc.error_msg = None
    db.commit()

    background_tasks.add_task(process_document_task, doc.id)
    log_event(db, "DOC", "INFO", f"重新触发文档向量化: {doc.filename}", operator=admin.username)
    return {"message": f"文档 [{doc.filename}] 已提交重新向量化任务"}


@router.get("/chroma/stats", response_model=ChromaStatsResponse, summary="获取向量库状态与总向量数")
def get_chroma_stats(admin: User = Depends(get_current_admin)):
    """查看向量库当前向量总数与状态"""
    count = vector_service.get_total_vectors()
    return {
        "collection_name": vector_service.COLLECTION_NAME,
        "total_vectors": count,
        "status": "ready"
    }


@router.post("/chroma/clear", summary="清空全部向量库数据")
def clear_chroma(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """管理员清空 Chroma 向量库所有切片"""
    vector_service.clear_all()
    # 将所有文档状态更新为切片数 0
    db.query(Document).update({Document.chunk_count: 0})
    db.commit()

    log_event(db, "SYSTEM", "WARNING", "管理员清空了整个知识向量库", operator=admin.username)
    return {"message": "向量库所有集合与切片已成功清空"}
