import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.documents import ALLOWED_EXTENSIONS
from app.models import ChatRequest, ChatResponse, TextIngestRequest, UploadResponse
from app.rag import chat, ingest_file, ingest_text

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


@app.get("/", include_in_schema=False)
def home() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>知识库智能体</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f8fb; color: #172033; }
    main { max-width: 960px; margin: 0 auto; padding: 32px 18px 56px; }
    header { margin-bottom: 24px; }
    h1 { margin: 0 0 8px; font-size: 30px; }
    p { line-height: 1.65; }
    .grid { display: grid; grid-template-columns: 1fr 1.3fr; gap: 18px; align-items: start; }
    .divider { margin: 18px 0; border-top: 1px dashed #d0d5dd; }
    input[type="text"] { width: 100%; box-sizing: border-box; border: 1px solid #cfd7e6; border-radius: 12px; padding: 10px 12px; background: #fff; font: inherit; margin-bottom: 10px; }
    .btn-secondary { background: #0f766e; }
    .card { background: white; border: 1px solid #e4e8f0; border-radius: 16px; padding: 20px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06); }
    label { display: block; font-weight: 650; margin-bottom: 8px; }
    input[type="file"], textarea { width: 100%; box-sizing: border-box; border: 1px solid #cfd7e6; border-radius: 12px; padding: 12px; background: #fff; font: inherit; }
    textarea { min-height: 120px; resize: vertical; }
    button { border: 0; border-radius: 12px; padding: 11px 16px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
    button:disabled { opacity: 0.55; cursor: not-allowed; }
    .muted { color: #667085; font-size: 14px; }
    .row { display: flex; gap: 10px; align-items: center; margin-top: 12px; }
    .status { margin-top: 12px; padding: 10px 12px; border-radius: 12px; background: #f1f5f9; white-space: pre-wrap; }
    .status:empty { display: none; padding: 0; margin: 0; }
    .answer { white-space: pre-wrap; line-height: 1.75; font-size: 15px; }
    .sources-block { margin-top: 20px; padding-top: 16px; border-top: 1px solid #e4e8f0; }
    .sources-title { font-size: 13px; font-weight: 650; color: #667085; margin-bottom: 10px; }
    .source { margin-bottom: 12px; padding: 12px 14px; background: #f8fafc; border-radius: 10px; border-left: 3px solid #93c5fd; }
    .source-name { font-weight: 600; font-size: 14px; margin-bottom: 6px; color: #1e3a5f; }
    .source-excerpt { font-size: 13px; color: #475467; line-height: 1.6; }
    @media (max-width: 760px) { .grid { grid-template-columns: 1fr; } main { padding-top: 20px; } }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>知识库智能体</h1>
      <p class="muted">支持上传 txt / md / pdf / Word / Excel 等，或直接粘贴文字入库。API 文档在 <a href="/docs">/docs</a>。</p>
    </header>
    <section class="grid">
      <div class="card">
        <h2>上传文档</h2>
        <label for="file">选择文件</label>
        <input id="file" type="file" accept=".txt,.md,.pdf,.docx,.xlsx,.xls,.csv,.pptx" />
        <div class="row">
          <button id="uploadBtn" type="button">上传并索引</button>
        </div>
        <div id="uploadStatus" class="status muted">等待上传。</div>
        <div class="divider"></div>
        <h2>文字入库</h2>
        <label for="textTitle">标题（可选）</label>
        <input id="textTitle" type="text" placeholder="例如：产品说明摘要" />
        <label for="textContent">正文</label>
        <textarea id="textContent" placeholder="粘贴或输入要加入知识库的文字…" style="min-height:100px"></textarea>
        <div class="row">
          <button id="textIngestBtn" type="button" class="btn-secondary">存入知识库</button>
        </div>
        <div id="textIngestStatus" class="status muted"></div>
      </div>
      <div class="card">
        <h2>知识库问答</h2>
        <label for="message">问题</label>
        <textarea id="message" placeholder="例如：这份文档主要讲了什么？"></textarea>
        <div class="row">
          <button id="chatBtn" type="button">发送问题</button>
        </div>
        <div id="chatStatus" class="status muted">等待提问。</div>
        <div id="answer" class="answer"></div>
        <div id="sources"></div>
      </div>
    </section>
  </main>
  <script>
    const uploadBtn = document.getElementById('uploadBtn');
    const textIngestBtn = document.getElementById('textIngestBtn');
    const chatBtn = document.getElementById('chatBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    const textIngestStatus = document.getElementById('textIngestStatus');
    const chatStatus = document.getElementById('chatStatus');
    const answer = document.getElementById('answer');
    const sources = document.getElementById('sources');

    uploadBtn.addEventListener('click', async () => {
      const file = document.getElementById('file').files[0];
      if (!file) {
        uploadStatus.textContent = '请先选择文件（支持 txt、md、pdf、Word、Excel 等）。';
        return;
      }
      const form = new FormData();
      form.append('file', file);
      uploadBtn.disabled = true;
      uploadStatus.textContent = '正在上传并索引...';
      try {
        const res = await fetch('/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || '上传失败');
        uploadStatus.textContent = `上传成功：${data.filename}\n索引数量：${data.documents_indexed}\n${data.message}`;
      } catch (err) {
        uploadStatus.textContent = `上传失败：${err.message}`;
      } finally {
        uploadBtn.disabled = false;
      }
    });

    textIngestBtn.addEventListener('click', async () => {
      const content = document.getElementById('textContent').value.trim();
      const title = document.getElementById('textTitle').value.trim();
      if (!content) {
        textIngestStatus.textContent = '请输入要入库的文字。';
        return;
      }
      textIngestBtn.disabled = true;
      textIngestStatus.textContent = '正在写入知识库...';
      try {
        const res = await fetch('/ingest/text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, title: title || null }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || '入库失败');
        textIngestStatus.textContent = `已入库：${data.filename}\n${data.message}`;
        document.getElementById('textContent').value = '';
      } catch (err) {
        textIngestStatus.textContent = `入库失败：${err.message}`;
      } finally {
        textIngestBtn.disabled = false;
      }
    });

    chatBtn.addEventListener('click', async () => {
      const message = document.getElementById('message').value.trim();
      if (!message) {
        chatStatus.textContent = '请输入问题。';
        return;
      }
      chatBtn.disabled = true;
      chatStatus.textContent = '正在检索并生成回答...';
      answer.textContent = '';
      sources.innerHTML = '';
      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || '问答失败');
        chatStatus.textContent = '';
        answer.textContent = data.answer || '（未生成回答）';
        const cites = data.citations || [];
        if (!cites.length) {
          sources.innerHTML = '';
        } else {
          sources.innerHTML = `
            <div class="sources-block">
              <div class="sources-title">参考来源</div>
              ${cites.map((item) => `
                <div class="source">
                  <div class="source-name">${escapeHtml(item.source || '未知文档')}</div>
                  <div class="source-excerpt">${escapeHtml(item.excerpt || '')}</div>
                </div>
              `).join('')}
            </div>
          `;
        }
      } catch (err) {
        chatStatus.textContent = `问答失败：${err.message}`;
      } finally {
        chatBtn.disabled = false;
      }
    });

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }
  </script>
</body>
</html>
        """
    )


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


@app.post("/ingest/text", response_model=UploadResponse)
async def ingest_text_endpoint(body: TextIngestRequest) -> UploadResponse:
    try:
        doc_count = ingest_text(body.content, title=body.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文字入库失败: {exc}") from exc

    display_name = (body.title or "文字输入").strip() or "文字输入"
    return UploadResponse(
        filename=display_name,
        message="文字已写入知识库并完成向量化索引",
        documents_indexed=doc_count,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest) -> ChatResponse:
    try:
        return chat(body.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"问答失败: {exc}") from exc
