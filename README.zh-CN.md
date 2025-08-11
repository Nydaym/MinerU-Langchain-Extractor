# Screenshot OCR Extractor（屏幕截图 OCR 信息抽取）

[English](README.md) | [简体中文](README.zh-CN.md)

使用本地 OCR 服务（默认 MinerU）与 LangChain，从截图/名片等图片中抽取人名、职位与公司。提供 FastAPI REST API 服务进行图片处理。

---

## 特性

- 对接本地 MinerU OCR（默认 `http://127.0.0.1:8000/file_parse`）
- LangChain 解析，支持 LLM 增强与启发式回退
- REST API 单图像处理
- JSON 响应格式

---

## 架构

1. 将图片发送至 OCR 服务 → 返回 Markdown 文本（`md_content`）
2. 解析为结构化信息：人名、职位、公司、置信度、缺失字段
3. 可选：通过 LangChain 使用 LLM 增强解析（OpenAI 兼容接口）
4. 通过 REST API 返回 JSON 响应

---

## 先决条件

- Python 3.10+
- 可用的本地 OCR 服务（默认 MinerU，`http://127.0.0.1:8000`，需提供 `POST /file_parse`，表单字段 `files`）
- 可选：OpenAI 兼容的 LLM 接口

---

## 快速开始（使用 uv）

使用 uv 直接运行（依赖由 `pyproject.toml` 解析）。

PowerShell（Windows）:

```powershell
# 启动 REST API（默认 0.0.0.0:8001）
uv run python -m src.server
# 或直接用 uvicorn
uv run uvicorn src.server:app --host 0.0.0.0 --port 8001
```

Bash:

```bash
uv run python -m src.server
# 或
uv run uvicorn src.server:app --host 0.0.0.0 --port 8001
```

未配置 LLM 时，会自动回退到启发式解析。

---

## 使用方式

### REST API

启动服务：

```powershell
uv run python -m src.server
# 文档: http://127.0.0.1:8001/docs
```

接口：`POST /extract`（表单字段 `file`）

```bash
curl -X POST "http://127.0.0.1:8001/extract" \
  -F "file=@example.jpg"
```

响应示例：

```json
{
  "success": true,
  "data": {
    "full_name": "Ada Lovelace",
    "job_title": "Software Engineer",
    "company_name": "Example Inc",
    "confidence": 0.67
  },
  "error_message": null,
  "ocr_text": "# Ada Lovelace\n# Software Engineer\n# Example Inc"
}
```

---

## 环境变量

API 服务端（见 `src/server.py`）：

- `LLM_MODEL`：默认 `qwen3:4b-instruct-2507-fp16`
- `LLM_BASE_URL`：默认 `http://0.0.0.0:11434/v1`
- `LLM_API_KEY`：任意非空将启用 LLM 客户端

`.env` 示例：

```dotenv
# API 服务端 LLM
LLM_MODEL=qwen3:4b-instruct-2507-fp16
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=your_key
```

---

## API 响应

API 返回 JSON 响应，结构如下：

```json
{
  "success": true,
  "data": {
    "full_name": "...",
    "job_title": "...",
    "company_name": "...",
    "confidence": 0.0
  },
  "error_message": null,
  "ocr_text": "..."
}
```

---

## 项目结构

```text
MinerU/
  ├─ pyproject.toml
  ├─ uv.lock
  └─ src/
     ├─ __init__.py
     ├─ server.py         # FastAPI 服务（包含 LangChain 解析）
     └─ ocr_client.py     # OCR 客户端（MinerU /file_parse）
```

---

## 故障排查

- 无法连接 OCR：确认 MinerU 服务已启动在 `http://127.0.0.1:8000`；检查 `POST /file_parse` 是否接受 `files` 字段。
- LLM 未启用：需在 API 服务端设置 `LLM_*` 环境变量。未设置时将自动回退到启发式解析。
- API 文档不可访问：确认服务已运行并访问 `http://127.0.0.1:8001/docs`。

---

## 许可

MIT License

---

## 致谢

- MinerU（OCR）
- LangChain
- FastAPI
