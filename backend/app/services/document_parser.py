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
    def _mult_matrix(m1, m2):
        a1, b1, c1, d1, e1, f1 = m1
        a2, b2, c2, d2, e2, f2 = m2
        return [
            a1*a2 + b1*c2,
            a1*b2 + b1*d2,
            c1*a2 + d1*c2,
            c1*b2 + d1*d2,
            e1*a2 + f1*c2 + e2,
            e1*b2 + f1*d2 + f2
        ]

    @staticmethod
    def _transform_point(p, m):
        a, b, c, d, e, f = m
        return (p[0]*a + p[1]*c + e, p[0]*b + p[1]*d + f)

    @classmethod
    def _extract_page_layout_text(cls, page) -> str:
        """
        基于 PDF 设备空间绝对物理坐标（Affine Transformation Matrix）高保真重排提取文本，
        解决 jsPDF、Canvas、Word/WPS 富文本高亮框/表格导出时文字乱序排版倒错的问题。
        """
        from collections import defaultdict
        pts = []

        def visitor(text, cm, tm, font_dict, font_size):
            if text:
                total_m = cls._mult_matrix(tm, cm)
                x_dev, y_dev = cls._transform_point((0, 0), total_m)
                pts.append((y_dev, x_dev, text))

        try:
            page.extract_text(visitor_text=visitor)
        except Exception:
            return page.extract_text() or ""

        if not pts:
            return page.extract_text() or ""

        # 按 4.0 像素进行行聚合分桶
        lines = defaultdict(list)
        for y, x, text in pts:
            bucket_y = round(y / 4.0) * 4.0
            lines[bucket_y].append((x, text))

        # PDF 视觉从上到下为绝对 Y 降序
        sorted_y_desc = sorted(lines.keys(), reverse=True)

        output_lines = []
        for y in sorted_y_desc:
            # 同行按 x 坐标升序（从左往右）
            row = sorted(lines[y], key=lambda item: item[0])
            row_text = "".join(item[1] for item in row).strip()
            if row_text:
                output_lines.append(row_text)

        result_text = "\n".join(output_lines)
        return result_text if len(result_text) > 10 else (page.extract_text() or "")

    @classmethod
    def parse_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        from pypdf import PdfReader
        results = []
        try:
            reader = PdfReader(file_path)
            for page_idx, page in enumerate(reader.pages):
                page_text = cls._extract_page_layout_text(page)
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
