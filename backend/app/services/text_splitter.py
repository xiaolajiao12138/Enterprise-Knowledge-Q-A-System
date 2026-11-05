from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument


class TextChunkSplitter:
    """
    针对中文文档优化的文本切分器
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "；",
                " ",
                ""
            ]
        )

    def split_parsed_pages(
        self,
        parsed_pages: List[Dict[str, Any]],
        document_id: int,
        filename: str
    ) -> List[LCDocument]:
        """
        将解析出的每一页/段文本进行切片，并赋予精准元数据
        """
        all_chunks: List[LCDocument] = []
        global_chunk_idx = 0

        for item in parsed_pages:
            text = item.get("text", "")
            page = item.get("page", 1)
            if not text.strip():
                continue

            sub_chunks = self.splitter.split_text(text)
            for chunk_content in sub_chunks:
                if not chunk_content.strip():
                    continue

                chunk_doc = LCDocument(
                    page_content=chunk_content.strip(),
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "page": page,
                        "chunk_index": global_chunk_idx
                    }
                )
                all_chunks.append(chunk_doc)
                global_chunk_idx += 1

        return all_chunks
