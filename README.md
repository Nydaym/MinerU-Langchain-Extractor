# Screenshot OCR Extractor

[English](README.md) | [简体中文](README.zh-CN.md)

Extract full name, job title, and company from screenshots (e.g., business cards, profiles) using a local OCR service (MinerU by default) and LangChain. Provides a FastAPI REST API for processing images.

---

## Features

- OCR integration with a local MinerU service (default `http://127.0.0.1:8000/file_parse`)
- LangChain parsing with LLM-enhanced mode and heuristic fallback
- REST API for single image processing
- JSON response format

---

## Architecture

1. Send image to OCR → receive Markdown text (`md_content`)
2. Parse to structured fields (full name, job title, company name, confidence, missing fields)
3. Optional LLM-enhanced parsing via LangChain (OpenAI-compatible API)
4. Return JSON response via REST API

---

## Prerequisites

- Python 3.10+
- A local OCR service (MinerU by default) at `http://127.0.0.1:8000` with `POST /file_parse` (form field `files`)
- Optional: OpenAI-compatible LLM endpoint for enhanced parsing

---

## Quickstart (uv)

Run directly with uv; dependencies are resolved from `pyproject.toml`.

PowerShell (Windows):

```powershell
# Start REST API (default 0.0.0.0:8001)
uv run python -m src.server
# or with uvicorn
uv run uvicorn src.server:app --host 0.0.0.0 --port 8001
```

Bash:

```bash
uv run python -m src.server
# or
uv run uvicorn src.server:app --host 0.0.0.0 --port 8001
```

If no LLM is configured, the parser falls back to heuristics.

---

## Usage

### REST API

Start the server:

```powershell
uv run python -m src.server
# Docs: http://127.0.0.1:8001/docs
```

Endpoint: `POST /extract` (form field `file`)

```bash
curl -X POST "http://127.0.0.1:8001/extract" \
  -F "file=@example.jpg"
```

Sample response:

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

## Environment Variables

API server (see `src/server.py`):

- `LLM_MODEL` (default `qwen3:4b-instruct-2507-fp16`)
- `LLM_BASE_URL` (default `http://0.0.0.0:11434/v1`)
- `LLM_API_KEY` (any non-empty value enables the LLM client)

`.env` example:

```dotenv
# For API server LLM
LLM_MODEL=qwen3:4b-instruct-2507-fp16
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=your_key
```

---

## API Response

The API returns a JSON response with the following structure:

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

## Project Structure

```text
MinerU/
  ├─ pyproject.toml
  ├─ uv.lock
  └─ src/
     ├─ __init__.py
     ├─ server.py         # FastAPI service (includes LangChain parsing)
     └─ ocr_client.py     # OCR client (MinerU /file_parse)
```

---

## Troubleshooting

- OCR connectivity: ensure MinerU is running at `http://127.0.0.1:8000`; `POST /file_parse` must accept form field `files`.
- LLM disabled: set `LLM_*` environment variables in the API server. Heuristic fallback is automatic.
- API docs: ensure the server is running and visit `http://127.0.0.1:8001/docs`.

---

## License

MIT License

---

## Acknowledgements

- MinerU (OCR)
- LangChain
- FastAPI
