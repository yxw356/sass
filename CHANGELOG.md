# 更新记录 (Changelog)

本文件记录 [知识库智能体 (KB Agent)](https://github.com/yxw356/sass) 的版本变更。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [未发布]

### 计划中

- 可选：Supabase 存储（文件 Storage + pgvector）
- 可选：对话历史持久化

---

## [0.5.0] - 2026-05-19

### 新增

- 支持上传 **Word**（`.docx`）、**Excel**（`.xlsx` / `.xls`）、**CSV**、**PPTX**
- 新增 **`POST /ingest/text`**：粘贴文字直接写入知识库（可选标题）
- 网页端增加「**文字入库**」区块
- 新增 `app/documents.py` 统一文档解析与格式校验
- 依赖：`llama-index-readers-file`、`python-docx`、`openpyxl`、`pandas`、`xlrd`

### 改进

- 问答展示：`answer` 仅含正文，引用在 `citations` 中单独展示，避免重复
- 网页引用区隐藏序号、`score` 等技术字段，文件名去掉上传 UUID 前缀
- 更新 README 与《新手操作与部署手册》

---

## [0.4.0] - 2026-05-19

### 新增

- 《[docs/新手操作与部署手册.md](docs/新手操作与部署手册.md)》：从零部署、使用、排错、检查清单

---

## [0.3.0] - 2026-05-19

### 新增

- `VLLMOpenAI`：对接本地 vLLM 时跳过 OpenAI 官方模型名校验
- 配置项 `VLLM_CONTEXT_WINDOW`（默认 32768）
- Embedding 本地优先：`models/bge-small-zh-v1.5/` 自动检测
- 脚本 `scripts/download_embedding_model.py`（支持 `HF_ENDPOINT` 镜像）

### 修复

- 修复 `/chat` 报错 `Unknown model 'Qwen3.6-35B-A3B'`
- 修复上传/问答因无法访问 Hugging Face 导致的 `client has been closed`
- 修复 LlamaIndex `index.insert()` 需逐条插入 Document 的问题

### 改进

- 网页交互首页（`GET /`）：上传 + 问答一体化界面

---

## [0.2.0] - 2026-05-18

### 新增

- Swagger / ReDoc **本地静态资源**（`static/`），解决 `/docs` 白屏（CDN 不可用）
- 自定义 `/docs`、`/redoc` 路由，不依赖 jsdelivr

### 变更

- 代码托管至 GitHub：[yxw356/sass](https://github.com/yxw356/sass)

---

## [0.1.0] - 2026-05-18

### 新增

- 基于 **FastAPI + LlamaIndex + Chroma** 的 RAG 知识库服务
- `POST /upload`：上传 `.txt`、`.md`、`.pdf` 并建立向量索引
- `POST /chat`：检索 + vLLM 生成回答，返回 `citations` 引用
- `GET /health` 健康检查
- 本地 **vLLM**（OpenAI 兼容 API，默认端口 8000）
- 本地 **Embedding**：`BAAI/bge-small-zh-v1.5`
- 配置：`.env` / `pydantic-settings`
- 数据目录：`data/uploads/`、`chroma_db/`

---

## 版本对照表

| 版本   | 日期       | 提交（main） | 摘要                         |
|--------|------------|--------------|------------------------------|
| 0.5.0  | 2026-05-19 | a65f77e      | Office 格式、文字入库、UI 优化 |
| 0.4.0  | 2026-05-19 | 9321982      | 新手操作与部署手册           |
| 0.3.0  | 2026-05-19 | e747947      | vLLM 适配、离线 Embedding    |
| 0.2.0  | 2026-05-18 | f2f5cbb      | 本地 Swagger、上架 GitHub    |
| 0.1.0  | 2026-05-18 | 650b0a7      | 初始 RAG 服务                |
