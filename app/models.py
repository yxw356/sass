from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户问题")


class Citation(BaseModel):
    index: int
    source: str
    excerpt: str
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class TextIngestRequest(BaseModel):
    content: str = Field(..., min_length=1, description="要写入知识库的文本")
    title: str | None = Field(
        default=None,
        max_length=200,
        description="可选标题，用于在引用来源中显示",
    )


class UploadResponse(BaseModel):
    filename: str
    message: str
    documents_indexed: int
