from __future__ import annotations

import logging
import re
from pathlib import Path

import chromadb
from llama_index.core import Settings as LlamaSettings
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.base.llms.types import MessageRole
from llama_index.core.llms import LLMMetadata
from llama_index.core.schema import NodeWithScore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore

from app.config import settings
from app.documents import (
    ALLOWED_EXTENSIONS,
    load_documents_from_file,
    load_documents_from_text,
)
from app.models import ChatResponse, Citation

logger = logging.getLogger(__name__)
_index: VectorStoreIndex | None = None
_embed_model: HuggingFaceEmbedding | None = None


class VLLMOpenAI(OpenAI):
    """OpenAI-compatible client for vLLM; skips OpenAI official model-name validation."""

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=settings.vllm_context_window,
            num_output=self.max_tokens or -1,
            is_chat_model=True,
            is_function_calling_model=True,
            model_name=self.model,
            system_role=MessageRole.SYSTEM,
        )

    @property
    def _tokenizer(self):
        return None


def _embedding_load_hint() -> str:
    local_dir = settings.default_local_embedding_dir
    return (
        "Embedding 模型加载失败。常见原因：无法访问 huggingface.co。\n"
        f"1) 在有网络的机器执行: HF_ENDPOINT=https://hf-mirror.com python scripts/download_embedding_model.py\n"
        f"2) 将模型放到: {local_dir}\n"
        "3) 或在 .env 设置 EMBEDDING_MODEL=/path/to/model 与 EMBEDDING_LOCAL_FILES_ONLY=true"
    )


def _create_embed_model() -> HuggingFaceEmbedding:
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    model_name = settings.embedding_model_resolved
    model_kwargs: dict = {}
    if settings.embedding_use_local_files_only:
        model_kwargs["local_files_only"] = True

    logger.info("Loading embedding model from %s", model_name)
    try:
        _embed_model = HuggingFaceEmbedding(model_name=model_name, **model_kwargs)
    except Exception as exc:
        raise RuntimeError(f"{_embedding_load_hint()}\n原始错误: {exc}") from exc
    return _embed_model


def _configure_llama() -> None:
    LlamaSettings.llm = VLLMOpenAI(
        model=settings.vllm_model,
        api_key=settings.vllm_api_key,
        api_base=settings.vllm_base_url,
    )
    LlamaSettings.embed_model = _create_embed_model()
    LlamaSettings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=64)


def _get_chroma_collection():
    settings.chroma_path_resolved.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(settings.chroma_path_resolved))
    return client.get_or_create_collection(settings.chroma_collection)


def get_index() -> VectorStoreIndex:
    global _index
    if _index is not None:
        return _index

    _configure_llama()
    collection = _get_chroma_collection()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    _index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )
    return _index


def _source_name(metadata: dict) -> str:
    for key in ("file_name", "filename", "source", "file_path"):
        value = metadata.get(key)
        if value:
            return _display_filename(Path(str(value)).name)
    return "unknown"


def _display_filename(name: str) -> str:
    """Strip upload prefix '{uuid}_' so citations show the original filename."""
    stem, sep, rest = name.partition("_")
    if sep and len(stem) == 32 and all(c in "0123456789abcdef" for c in stem.lower()):
        return rest or name
    return name


def _excerpt(text: str, max_len: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."


def _insert_documents(documents: list) -> int:
    index = get_index()
    for doc in documents:
        index.insert(doc)
    return len(documents)


def ingest_file(file_path: Path) -> int:
    documents = load_documents_from_file(file_path)
    return _insert_documents(documents)


def ingest_text(content: str, title: str | None = None) -> int:
    documents = load_documents_from_text(content, title=title)
    dest = settings.upload_path / documents[0].metadata["file_name"]
    dest.write_text(content.strip(), encoding="utf-8")
    documents[0].metadata["file_path"] = str(dest)
    return _insert_documents(documents)


def _build_citations(source_nodes: list[NodeWithScore]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()

    for node in source_nodes:
        meta = node.node.metadata or {}
        source = _source_name(meta)
        excerpt = _excerpt(node.node.get_content())
        key = (source, excerpt)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                index=len(citations) + 1,
                source=source,
                excerpt=excerpt,
                score=float(node.score) if node.score is not None else None,
            )
        )
    return citations


def chat(message: str) -> ChatResponse:
    index = get_index()
    query_engine = index.as_query_engine(similarity_top_k=settings.similarity_top_k)
    response = query_engine.query(message)

    source_nodes = list(response.source_nodes or [])
    citations = _build_citations(source_nodes)
    answer_text = str(response).strip()

    return ChatResponse(answer=answer_text, citations=citations)
