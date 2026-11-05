import os
import re
import json
import httpx
from typing import List, Dict, Any, Tuple
from app.config import settings
from app.core.logger import logger
from app.database import SessionLocal
from app.models.system_setting import SystemSetting
from app.services.vector_store import vector_service


class RAGService:
    """
    RAG 知识库问答核心服务：
    负责知识库混合检索、同义词模糊匹配、防幻觉 Prompt 构建、多轮对话整合、LLM 调用与引用来源提取。
    """

    NO_INFO_MESSAGE = "知识库中暂未检索到与该问题相关的信息，无法为您解答。请尝试更换提问方式或联系管理员补充相关文档。"

    # 常见企业文档高频泛词与疑问虚词停用列表
    STOP_WORDS = {
        "是几", "几点", "什么", "多少", "是多", "少钱", "如何", "怎么",
        "有哪些", "公司", "企业", "我们", "请问", "我想", "知道", "一下"
    }

    def _get_llm_config(self) -> Dict[str, Any]:
        """从数据库读取最新的系统 LLM 配置"""
        db = SessionLocal()
        try:
            records = db.query(SystemSetting).filter(
                SystemSetting.key.in_([
                    "llm_provider", "llm_base_url", "llm_api_key",
                    "llm_model", "temperature", "top_p", "top_k"
                ])
            ).all()
            cfg = {r.key: r.value for r in records}
            return {
                "provider": cfg.get("llm_provider", settings.DEFAULT_LLM_PROVIDER),
                "base_url": cfg.get("llm_base_url", settings.DEFAULT_LLM_BASE_URL),
                "api_key": cfg.get("llm_api_key", settings.DEFAULT_LLM_API_KEY),
                "model": cfg.get("llm_model", settings.DEFAULT_LLM_MODEL),
                "temperature": float(cfg.get("temperature", settings.DEFAULT_TEMPERATURE)),
                "top_p": float(cfg.get("top_p", settings.DEFAULT_TOP_P)),
                "top_k": int(cfg.get("top_k", settings.DEFAULT_TOP_K)),
            }
        except Exception:
            return {
                "provider": settings.DEFAULT_LLM_PROVIDER,
                "base_url": settings.DEFAULT_LLM_BASE_URL,
                "api_key": settings.DEFAULT_LLM_API_KEY,
                "model": settings.DEFAULT_LLM_MODEL,
                "temperature": settings.DEFAULT_TEMPERATURE,
                "top_p": settings.DEFAULT_TOP_P,
                "top_k": settings.DEFAULT_TOP_K,
            }
        finally:
            db.close()

    def _compute_match_score(self, query: str, content: str) -> float:
        """
        计算查询与文档内容的匹配度：
        支持完全匹配、跳字同义模糊匹配（如 年假 -> 年[休]假, 餐补 -> 餐[饮]补[贴]）、字符集覆盖率
        """
        clean_q = query.strip()
        if not clean_q:
            return 0.0

        # 1. 完全包含整串
        if clean_q in content:
            return 1.0

        # 如果是无意义重复字符（如 111, 222, aaa）或纯无意义数字且未完全匹配，直接为 0
        if clean_q.isdigit() or re.match(r'^(.)\1+$', clean_q):
            return 0.0

        # 提取汉字列表
        cn_chars = [c for c in clean_q if '\u4e00' <= c <= '\u9fa5']
        if not cn_chars:
            return 0.0

        # 2. 中文跳字同义模糊匹配（如“年假”匹配“年休假”，“餐补”匹配“餐饮补贴”）
        if len(cn_chars) >= 2:
            fuzzy_pat = r'.?'.join(re.escape(c) for c in cn_chars)
            if re.search(fuzzy_pat, content):
                return 0.9

        # 3. 核心汉字覆盖比例
        hit_chars = [c for c in cn_chars if c in content]
        rate = len(hit_chars) / len(cn_chars)
        if rate >= 0.65:
            return rate * 0.6

        return 0.0

    def retrieve_context(self, question: str, top_k: int = 4) -> Tuple[str, List[Dict[str, Any]]]:
        """
        混合检索：结合向量语义相似度 + 中文关键词与同义词重合评分
        返回：(组装后的上下文文本, 结构化引用来源列表)
        """
        search_results = vector_service.similarity_search_with_score(question, k=top_k)

        if not search_results:
            return "", []

        scored_candidates = []

        for doc, v_score in search_results:
            content = doc.page_content.strip()
            # 计算文本匹配度 (完全匹配/跳字同义匹配/字符覆盖)
            text_score = self._compute_match_score(question, content)

            # 综合评分：结合向量分与字词重合分
            combined_score = round(v_score * 0.35 + text_score * 0.65, 4)

            scored_candidates.append({
                "doc": doc,
                "v_score": v_score,
                "text_score": text_score,
                "combined_score": combined_score
            })

        # 按综合得分降序排列
        scored_candidates.sort(key=lambda x: x["combined_score"], reverse=True)

        # 过滤机制：必须具有字面相关性 (text_score > 0) 或向量得分高 (v_score >= 0.3)
        valid_candidates = [
            c for c in scored_candidates
            if c["text_score"] > 0 or c["v_score"] >= 0.3
        ]

        if not valid_candidates:
            logger.info(f"问题 [{question}] 知识库无相关知识匹配 (无同义关键词命中且向量得分低)")
            return "", []

        context_blocks = []
        sources = []

        for idx, item in enumerate(valid_candidates[:top_k]):
            doc = item["doc"]
            meta = doc.metadata or {}
            filename = meta.get("filename", "未知文件")
            page = meta.get("page", 1)
            chunk_idx = meta.get("chunk_index", idx)
            content = doc.page_content.strip()

            context_blocks.append(
                f"[参考片段 {idx + 1} | 来源文档: 《{filename}》 第 {page} 页/段]\n{content}"
            )

            sources.append({
                "document_id": meta.get("document_id"),
                "filename": filename,
                "chunk_index": chunk_idx,
                "content_preview": content[:160] + ("..." if len(content) > 160 else ""),
                "score": max(item["combined_score"], item["v_score"])
            })

        combined_context = "\n\n".join(context_blocks)
        return combined_context, sources

    def _call_ollama(self, prompt_messages: List[Dict[str, str]], cfg: Dict[str, Any]) -> str:
        """调用 Ollama 原生端点"""
        url = cfg["base_url"].rstrip("/") + "/api/chat"
        payload = {
            "model": cfg["model"],
            "messages": prompt_messages,
            "stream": False,
            "options": {
                "temperature": cfg["temperature"],
                "top_p": cfg["top_p"]
            }
        }
        with httpx.Client(timeout=40.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "").strip()
            else:
                raise RuntimeError(f"Ollama 返回异常: HTTP {resp.status_code} - {resp.text}")

    def _call_openai_compatible(self, prompt_messages: List[Dict[str, str]], cfg: Dict[str, Any]) -> str:
        """调用 OpenAI 兼容接口 (DeepSeek, 阿里百炼, LocalAI, One-API 等)"""
        base_url = cfg["base_url"].rstrip("/")
        if not base_url.startswith("http"):
            base_url = "https://" + base_url

        if base_url.endswith("/chat/completions"):
            url = base_url
        elif base_url.endswith("/v1"):
            url = base_url + "/chat/completions"
        else:
            url = base_url + "/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}"
        }
        payload = {
            "model": cfg["model"],
            "messages": prompt_messages,
            "temperature": cfg["temperature"],
            "top_p": cfg["top_p"]
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                return ""
            else:
                raise RuntimeError(f"大模型 API 返回异常: HTTP {resp.status_code} - {resp.text}")

    def _fallback_extract_answer(self, question: str, context: str, sources: List[Dict[str, Any]]) -> str:
        """
        离线智能提炼模式：
        在检索出的有效切片中，精准抓取与问题关键词紧密关联的语句并进行结构化呈现。
        """
        if not context or not sources:
            return self.NO_INFO_MESSAGE

        primary_source = sources[0]
        filename = primary_source["filename"]

        raw_lines = re.split(r'[\n。！!？?]', context)
        highlighted_lines = []

        for line in raw_lines:
            line = line.strip()
            if not line or len(line) < 4:
                continue
            # 只要包含问题中的任意关键词或跳字命中
            if self._compute_match_score(question, line) > 0:
                highlighted_lines.append(line)

        if not highlighted_lines:
            # 如果没找到单行，提取前几行
            highlighted_lines = [l.strip() for l in raw_lines if len(l.strip()) > 8][:3]

        seen = set()
        unique_highlights = []
        for h in highlighted_lines:
            if h not in seen:
                seen.add(h)
                unique_highlights.append(f"- **{h}**")
        answer_core = "\n".join(unique_highlights[:5])

        return (
            f"根据企业内部知识库文档《{filename}》的明确规定：\n\n"
            f"{answer_core}\n\n"
            f"> *(提示：当前处于本地离线直接检索提炼模式；在【系统配置】中启动 Ollama 或接入大模型 API 即可享受完整自然语言流式归纳)*"
        )

    def answer_question(
        self,
        question: str,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        完整的 RAG 问答链路：
        1. 混合检索（语义+关键词）TopN 片段
        2. 若无有效匹配内容，严格拒绝回答并返回标准提示
        3. 组装防幻觉 Prompt + 多轮历史
        4. 调用配置的 LLM（自动识别 Ollama 与 OpenAI 兼容接口）
        5. 若 LLM 响应异常或离线，平滑进入智能本地提炼生成
        6. 返回最终答案与引用来源列表
        """
        cfg = self._get_llm_config()
        top_k = cfg["top_k"]

        # 1. 检索知识库上下文
        context_str, sources = self.retrieve_context(question, top_k=top_k)

        # 严格防幻觉断言：若无相关内容，直接拒绝
        if not sources or not context_str.strip():
            return {
                "answer": self.NO_INFO_MESSAGE,
                "sources": []
            }

        # 2. 构建系统约束 Prompt
        system_prompt = (
            "你是一个企业内部专业的知识库问答助手。\n"
            "【强制规则】\n"
            "1. 你必须严格、完全基于下方提供的【参考片段】内容来回答用户的问题。\n"
            "2. 严禁捏造、臆测任何事实。如果提供的【参考片段】中没有包含回答该问题所需的有效信息，你必须原样回答："
            f"\"{self.NO_INFO_MESSAGE}\"，绝对不允许自行推测或基于网络公开常识编造。\n"
            "3. 回答要严谨专业、条理清晰，在回答末尾请简要注明参考的文档名称。\n\n"
            f"【参考片段如下】：\n{context_str}"
        )

        # 3. 组织多轮对话历史
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            recent_history = chat_history[-6:]
            for msg in recent_history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": question})

        # 4. 执行模型生成（智能判定 provider）
        answer = ""
        provider = cfg["provider"].lower()

        is_external_openai = (
            provider in ["openai", "openai_compatible"] or
            cfg["base_url"].startswith("https://") or
            "v1" in cfg["base_url"] or
            (cfg["api_key"] and cfg["api_key"] not in ["EMPTY", ""])
        )

        try:
            if is_external_openai and provider != "ollama":
                answer = self._call_openai_compatible(messages, cfg)
            elif provider == "ollama":
                try:
                    answer = self._call_ollama(messages, cfg)
                except Exception as ollama_err:
                    if is_external_openai:
                        logger.info(f"Ollama 原生调用失败，尝试以 OpenAI 兼容协议重试: {ollama_err}")
                        answer = self._call_openai_compatible(messages, cfg)
                    else:
                        raise ollama_err
            else:
                answer = self._call_openai_compatible(messages, cfg)
        except Exception as e:
            logger.info(f"大模型接口未连通或响应异常 ({e})，启用本地智能提取回答")
            answer = self._fallback_extract_answer(question, context_str, sources)

        if answer == self.NO_INFO_MESSAGE or not answer.strip():
            return {
                "answer": self.NO_INFO_MESSAGE,
                "sources": []
            }

        return {
            "answer": answer,
            "sources": sources
        }


# 全局单例
rag_service = RAGService()
