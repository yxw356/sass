import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ChatRequest, ChatResponse, UploadResponse
from app.rag import ALLOWED_EXTENSIONS, chat, ingest_file

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="知识库智能体",
    description="基于 LlamaIndex + Chroma 的 RAG 知识库问答服务",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html() -> HTMLResponse:
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )


@app.on_event("startup")
def on_startup() -> None:
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_path_resolved.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"仅支持上传 {', '.join(sorted(ALLOWED_EXTENSIONS))} 文件",
        )

    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename).name}"
    dest = settings.upload_path / safe_name

    try:
        with dest.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        doc_count = ingest_file(dest)
    except ValueError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"文档索引失败: {exc}") from exc

    return UploadResponse(
        filename=file.filename,
        message="文档已上传并完成向量化索引",
        documents_indexed=doc_count,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest) -> ChatResponse:
    try:
        return chat(body.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc
