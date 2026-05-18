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


class UploadResponse(BaseModel):
    filename: str
    message: str
    documents_indexed: int
