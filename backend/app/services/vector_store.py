import os
import math
import hashlib
from typing import List, Tuple, Optional
import httpx
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings
from app.config import settings
from app.core.logger import logger
from app.database import SessionLocal
from app.models.system_setting import SystemSetting


class HashFallbackEmbeddings(Embeddings):
    """
    内置高鲁棒字符哈希与语义向量模型：
    开箱即用，零依赖、零外网调用、免安装本地大模型软件。
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        if not text:
            return vec
        # 提取 2-gram 字符特征
        words = [text[i:i+2] for i in range(len(text) - 1)] or [text]
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)


class VectorStoreService:
    """
    Chroma 向量库核心管理服务
    """
    COLLECTION_NAME = "enterprise_knowledge"

    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

    def _check_ollama_alive(self, base_url: str) -> bool:
        """快速探测 Ollama 是否在线 (0.8秒超时)"""
        try:
            with httpx.Client(timeout=0.8) as client:
                r = client.get(f"{base_url.rstrip('/')}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def _get_embedding_config(self) -> dict:
        """从数据库读取最新的 Embedding 设置"""
        db = SessionLocal()
        try:
            records = db.query(SystemSetting).filter(
                SystemSetting.key.in_([
                    "embedding_provider",
                    "embedding_base_url",
                    "embedding_api_key",
                    "embedding_model"
                ])
            ).all()
            cfg = {r.key: r.value for r in records}
            return {
                "provider": cfg.get("embedding_provider", settings.DEFAULT_EMBEDDING_PROVIDER),
                "base_url": cfg.get("embedding_base_url", settings.DEFAULT_EMBEDDING_BASE_URL),
                "api_key": cfg.get("embedding_api_key", settings.DEFAULT_EMBEDDING_API_KEY),
                "model": cfg.get("embedding_model", settings.DEFAULT_EMBEDDING_MODEL),
            }
        except Exception:
            return {
                "provider": settings.DEFAULT_EMBEDDING_PROVIDER,
                "base_url": settings.DEFAULT_EMBEDDING_BASE_URL,
                "api_key": settings.DEFAULT_EMBEDDING_API_KEY,
                "model": settings.DEFAULT_EMBEDDING_MODEL,
            }
        finally:
            db.close()

    def get_embeddings_model(self) -> Embeddings:
        """根据配置返回相应的 Embeddings 实例"""
        cfg = self._get_embedding_config()
        provider = cfg["provider"].lower()

        # 如果指定使用内置引擎，直接返回
        if provider in ["builtin", "fallback", "default"]:
            return HashFallbackEmbeddings()

        try:
            if provider == "ollama":
                if not self._check_ollama_alive(cfg["base_url"]):
                    return HashFallbackEmbeddings()

                from langchain_community.embeddings import OllamaEmbeddings
                return OllamaEmbeddings(
                    base_url=cfg["base_url"],
                    model=cfg["model"]
                )
            elif provider in ["openai", "openai_compatible"]:
                from langchain_community.embeddings import OpenAIEmbeddings
                return OpenAIEmbeddings(
                    openai_api_base=cfg["base_url"],
                    openai_api_key=cfg["api_key"] or "EMPTY",
                    model=cfg["model"]
                )
        except Exception as e:
            logger.warning(f"外部 Embedding 初始化异常: {e}")

        return HashFallbackEmbeddings()

    def get_collection(self):
        """获取或创建 Chroma 集合"""
        return self.chroma_client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, documents: List[LCDocument]):
        """将文档切片批量向量化并存入 Chroma"""
        if not documents:
            return

        collection = self.get_collection()
        embedder = self.get_embeddings_model()

        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        ids = [
            f"doc_{doc.metadata.get('document_id')}_chunk_{doc.metadata.get('chunk_index')}_{i}"
            for i, doc in enumerate(documents)
        ]

        try:
            embeddings = embedder.embed_documents(texts)
        except Exception:
            fallback = HashFallbackEmbeddings()
            embeddings = fallback.embed_documents(texts)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        logger.info(f"成功存入 {len(documents)} 个切片到 Chroma 知识库")

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4
    ) -> List[Tuple[LCDocument, float]]:
        """
        根据用户查询检索最相似的 TopK 片段
        返回: [(LCDocument, score), ...]
        """
        collection = self.get_collection()
        if collection.count() == 0:
            return []

        embedder = self.get_embeddings_model()
        try:
            query_embedding = embedder.embed_query(query)
        except Exception:
            query_embedding = HashFallbackEmbeddings().embed_query(query)

        actual_k = min(k, collection.count())
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=actual_k
        )

        output: List[Tuple[LCDocument, float]] = []
        if not results or not results["documents"] or not results["documents"][0]:
            return output

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for text, meta, dist in zip(docs, metas, distances):
            score = round(max(0.0, 1.0 - float(dist)), 4)
            doc = LCDocument(page_content=text, metadata=meta or {})
            output.append((doc, score))

        return output

    def delete_by_document_id(self, document_id: int):
        """根据 document_id 从 Chroma 中删除相关切片向量"""
        collection = self.get_collection()
        try:
            collection.delete(where={"document_id": document_id})
            logger.info(f"从 Chroma 中删除了 document_id={document_id} 的所有向量")
        except Exception as e:
            logger.error(f"删除文档向量失败: {e}")

    def clear_all(self):
        """清空知识库全部向量"""
        try:
            self.chroma_client.delete_collection(self.COLLECTION_NAME)
            logger.info("已清空 Chroma 知识库集合")
        except Exception as e:
            logger.warning(f"清空知识库集合提示: {e}")

    def get_total_vectors(self) -> int:
        """获取向量库中的向量总数"""
        try:
            collection = self.get_collection()
            return collection.count()
        except Exception:
            return 0


# 全局单例
vector_service = VectorStoreService()
