import os
import shutil
from pathlib import Path
from app.config import DEMO_DIR, UPLOAD_DIR
from app.database import SessionLocal
from app.models.document import Document
from app.services.background_tasks import process_document_task


def import_demo_documents():
    """将 demo_docs 目录下的测试文档自动导入知识库并进行切片与向量化"""
    print(">>> 正在扫描并导入演示知识库文档...")
    db = SessionLocal()
    try:
        files = list(DEMO_DIR.glob("*.*"))
        if not files:
            print("未发现演示文档。")
            return

        for f in files:
            # 检查是否已存在同名文档
            exist = db.query(Document).filter(Document.filename == f.name).first()
            if exist:
                print(f"  [跳过] 文档已存在: {f.name}")
                continue

            # 复制到上传目录
            dest_path = UPLOAD_DIR / f.name
            shutil.copy2(f, dest_path)

            doc = Document(
                filename=f.name,
                file_path=str(dest_path),
                file_size=f.stat().st_size,
                file_type=f.suffix.lower(),
                status="processing",
                chunk_count=0
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            print(f"  [导入] 文档导入成功: {f.name} (ID={doc.id})，开始切片与向量化...")
            process_document_task(doc.id)
            print(f"  [完成] 文档已入库: {f.name}")

        print(">>> 演示知识库文档全部导入完成！现在可以直接提问测试！")
    finally:
        db.close()


if __name__ == "__main__":
    import_demo_documents()
