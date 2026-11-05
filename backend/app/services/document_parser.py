import os
from pathlib import Path
from typing import List, Dict, Any
from app.core.logger import logger


class DocumentParser:
    """
    文档解析器：支持 PDF, DOCX, TXT, MD 等多种格式
    返回结构化片段列表: [{"text": str, "page": int}]
    """

    @staticmethod
    def parse_txt_or_md(file_path: str) -> List[Dict[str, Any]]:
        encodings = ["utf-8", "gbk", "gb18030", "utf-16", "ansi"]
        content = None
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except Exception:
                continue

        if content is None:
            raise ValueError(f"无法使用常见编码读取文件: {file_path}")

        return [{"text": content.strip(), "page": 1}]

    @staticmethod
    def parse_pdf(file_path: str) -> List[Dict[str, Any]]:
        from pypdf import PdfReader
        results = []
        try:
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    results.append({
                        "text": page_text.strip(),
                        "page": page_idx + 1
                    })
        except Exception as e:
            logger.error(f"PDF 解析失败: {e}")
            raise ValueError(f"PDF 文件解析失败: {str(e)}")

        if not results:
            # 可能是扫描件或空文件
            results.append({"text": "[未能在 PDF 中提取到可复制文本，可能为纯扫描图片]", "page": 1})

        return results

    @staticmethod
    def parse_docx(file_path: str) -> List[Dict[str, Any]]:
        import docx
        try:
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text.append(para.text.strip())

            # 解析表格中的文字
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        full_text.append(" | ".join(row_text))

            combined = "\n\n".join(full_text)
            return [{"text": combined, "page": 1}]
        except Exception as e:
            logger.error(f"DOCX 解析失败: {e}")
            raise ValueError(f"Word 文档解析失败: {str(e)}")

    @classmethod
    def parse(cls, file_path: str) -> List[Dict[str, Any]]:
        ext = Path(file_path).suffix.lower()
        if ext in [".txt", ".md"]:
            return cls.parse_txt_or_md(file_path)
        elif ext == ".pdf":
            return cls.parse_pdf(file_path)
        elif ext in [".docx", ".doc"]:
            return cls.parse_docx(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
