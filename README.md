# 知识库智能体 (KB Agent)

基于 **FastAPI + LlamaIndex + Chroma** 的本地 RAG 知识库问答服务。支持上传 `txt` / `md` / `pdf` 文档，通过本地 vLLM（OpenAI 兼容接口）进行问答，并在回答中附带引用来源。

## 架构

```
客户端 → FastAPI (8080)
              ├── /upload  → 文档解析 → 分块 → Embedding → Chroma
              └── /chat    → 检索 → vLLM 生成 → 带引用的回答
```

- **LLM**：vLLM OpenAI 兼容 API（默认 `http://127.0.0.1:8000/v1`）
- **Embedding**：本地 HuggingFace 模型（默认 `BAAI/bge-small-zh-v1.5`）
- **向量库**：Chroma 持久化存储（`./chroma_db`）

## 环境要求

- Python 3.10+
- 已启动的 vLLM 服务（OpenAI 兼容模式）
- 约 2GB 磁盘空间（用于 Embedding 模型首次下载）

## 快速开始

### 1. 启动 vLLM

确保 vLLM 已在本地运行，并暴露 OpenAI 兼容接口，例如：

```bash
# 示例（按你的实际部署调整）
vllm serve Qwen3.6-35B-A3B --host 0.0.0.0 --port 8000 --api-key vllm_api_key_12345
```

默认连接参数：

| 配置项 | 默认值 |
|--------|--------|
| `VLLM_BASE_URL` | `http://127.0.0.1:8000/v1` |
| `VLLM_API_KEY` | `vllm_api_key_12345` |
| `VLLM_MODEL` | `Qwen3.6-35B-A3B` |

### 2. 安装依赖

```bash
cd kb-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置（可选）

```bash
cp .env.example .env
# 按需修改 .env
```

### 4. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

服务地址：`http://127.0.0.1:8080`  
API 文档：`http://127.0.0.1:8080/docs`

> 知识库 API 使用 **8080** 端口，避免与 vLLM 的 **8000** 端口冲突。

## API 说明

### `POST /upload` — 上传文档

支持格式：`.txt`、`.md`、`.pdf`

```bash
curl -X POST "http://127.0.0.1:8080/upload" \
  -F "file=@/path/to/document.pdf"
```

响应示例：

```json
{
  "filename": "document.pdf",
  "message": "文档已上传并完成向量化索引",
  "documents_indexed": 1
}
```

### `POST /chat` — 知识库问答

```bash
curl -X POST "http://127.0.0.1:8080/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "文档里提到了哪些要点？"}'
```

响应示例：

```json
{
  "answer": "根据文档内容，主要要点包括……\n\n引用来源：\n[1] document.pdf (相关度: 0.812)\n    ……原文片段……",
  "citations": [
    {
      "index": 1,
      "source": "document.pdf",
      "excerpt": "……原文片段……",
      "score": 0.812
    }
  ]
}
```

`answer` 字段末尾会列出引用来源；`citations` 数组提供结构化引用，便于前端展示。

### `GET /health` — 健康检查

```bash
curl http://127.0.0.1:8080/health
```

## 目录结构

```
kb-agent/
├── app/
│   ├── config.py      # 配置
│   ├── models.py      # 请求/响应模型
│   ├── rag.py         # LlamaIndex RAG 逻辑
│   └── main.py        # FastAPI 入口
├── data/uploads/      # 上传文件存储
├── chroma_db/         # Chroma 向量库（运行后自动生成）
├── requirements.txt
├── .env.example
└── README.md
```

## Embedding 模型（离线 / 内网）

首次上传或问答会加载 Embedding 模型。若无法访问 `huggingface.co`，会出现类似：

`文档索引失败: Cannot send a request, as the client has been closed.`

终端里通常还有 `Network is unreachable` 访问 `BAAI/bge-small-zh-v1.5`。

**在有网络的机器预下载到项目目录：**

```bash
HF_ENDPOINT=https://hf-mirror.com python scripts/download_embedding_model.py
```

模型会保存到 `models/bge-small-zh-v1.5/`。重启服务后会**自动优先使用**该本地目录（无需改配置）。

也可在 `.env` 中指定：

```env
EMBEDDING_MODEL=./models/bge-small-zh-v1.5
EMBEDDING_LOCAL_FILES_ONLY=true
```

## 常见问题

**Q: 首次启动很慢？**  
A: 需要加载 Embedding 模型（`BAAI/bge-small-zh-v1.5`）。建议用上面的脚本预下载到 `models/`，避免运行时访问 Hugging Face。

**Q: `/chat` 报错连接 LLM 失败？**  
A: 确认 vLLM 已在 `http://127.0.0.1:8000` 运行，且 `VLLM_MODEL` 与 vLLM 实际加载的模型名一致。

**Q: 如何清空知识库？**  
A: 停止服务后删除 `chroma_db/` 目录和 `data/uploads/` 中的文件，重启即可。

## License

MIT
