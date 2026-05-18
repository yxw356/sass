"""Load and validate documents for knowledge-base ingestion."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from llama_index.core import Document, SimpleDirectoryReader

ALLOWED_EXTENSIONS = frozenset(
    {
        ".txt",
        ".md",
        ".pdf",
        ".docx",
        ".xlsx",
        ".xls",
        ".csv",
        ".pptx",
    }
)

ALLOWED_EXTENSIONS_LABEL = ", ".join(sorted(ALLOWED_EXTENSIONS))


def _sanitize_title(title: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.\- ]", "_", title.strip())
    return cleaned[:80] or "文字输入"


def load_documents_from_file(file_path: Path) -> list[Document]:
    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    documents = SimpleDirectoryReader(input_files=[str(file_path)]).load_data()
    if not documents:
        raise ValueError("未能从文件中解析出任何文本内容，请检查文件是否为空或格式是否正确")

    for doc in documents:
        doc.metadata["file_name"] = file_path.name
        doc.metadata["file_path"] = str(file_path)
    return documents


def load_documents_from_text(content: str, title: str | None = None) -> list[Document]:
    text = content.strip()
    if not text:
        raise ValueError("文字内容不能为空")

    label = _sanitize_title(title) if title else "文字输入"
    file_name = f"{uuid.uuid4().hex}_{label}.txt"
    document = Document(
        text=text,
        metadata={
            "file_name": file_name,
            "source_type": "text_input",
        },
    )
    return [document]
