import traceback
from datetime import datetime
from app.database import SessionLocal
from app.models.document import Document
from app.models.system_setting import SystemSetting
from app.services.document_parser import DocumentParser
from app.services.text_splitter import TextChunkSplitter
from app.services.vector_store import vector_service
from app.core.logger import logger, log_event
from app.config import settings


def process_document_task(document_id: int):
    """
    后台异步任务：解析文档、文本切片、计算向量并存储入 Chroma 向量库
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"后台任务未能找到文档 ID={document_id}")
            return

        doc.status = "processing"
        doc.error_msg = None
        db.commit()

        # 读取切片配置
        chunk_size_setting = db.query(SystemSetting).filter(SystemSetting.key == "chunk_size").first()
        chunk_overlap_setting = db.query(SystemSetting).filter(SystemSetting.key == "chunk_overlap").first()

        chunk_size = int(chunk_size_setting.value) if chunk_size_setting else settings.DEFAULT_CHUNK_SIZE
        chunk_overlap = int(chunk_overlap_setting.value) if chunk_overlap_setting else settings.DEFAULT_CHUNK_OVERLAP

        logger.info(f"开始解析文档 [{doc.filename}], 切片参数: size={chunk_size}, overlap={chunk_overlap}")

        # 1. 结构化文本解析
        parsed_pages = DocumentParser.parse(doc.file_path)

        # 2. 文本递归分块
        splitter = TextChunkSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = splitter.split_parsed_pages(
            parsed_pages=parsed_pages,
            document_id=doc.id,
            filename=doc.filename
        )

        if not chunks:
            raise ValueError("文档内容为空或无法提取有效文字")

        # 3. 先清除历史该文档的可能旧向量（如重新向量化场景）
        vector_service.delete_by_document_id(doc.id)

        # 4. 向量化并存入 Chroma
        vector_service.add_documents(chunks)

        # 5. 更新文档成功状态
        doc.status = "completed"
        doc.chunk_count = len(chunks)
        doc.updated_at = datetime.now()
        db.commit()

        log_event(
            db,
            module="DOC",
            level="INFO",
            message=f"文档 [{doc.filename}] 处理完成，成功切分并向量化 {len(chunks)} 个片段",
            operator="system"
        )
        logger.info(f"文档 [{doc.filename}] 向量化完成，切片数: {len(chunks)}")

    except Exception as e:
        err_msg = str(e)
        logger.error(f"处理文档 ID={document_id} 出错: {err_msg}\n{traceback.format_exc()}")
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.status = "failed"
                doc.error_msg = err_msg
                doc.updated_at = datetime.now()
                db.commit()

            log_event(
                db,
                module="DOC",
                level="ERROR",
                message=f"文档处理失败: ID={document_id}",
                details=traceback.format_exc(),
                operator="system"
            )
        except Exception:
            pass
    finally:
        db.close()
