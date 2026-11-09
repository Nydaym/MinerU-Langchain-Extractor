# Universal OCR Information Extractor

📚 Document Language: [English](README.md) | [简体中文](README.zh-CN.md)  
📖 Developer Guide:  [English](DEVELOPER_GUIDE_EN.md) | [中文版](DEVELOPER_GUIDE.md)

A universal information extraction system that uses OCR and LangChain to extract information from PDFs and images. Supports person info, sentiment analysis, company details, product information, and contact details through a FastAPI REST API.

---

## Features

- **Universal Information Extraction**: Support for multiple extraction types (person, sentiment, company, product, contact)
- **OCR Integration**: Uses the official hosted MinerU API by default; an existing local OCR service remains available as an option
- **LangChain Parsing**: LLM-enhanced mode with heuristic fallback for each extraction type
- **REST API**: RESTful endpoints for image processing with flexible extraction type selection
- **Backward Compatibility**: Legacy endpoints remain functional
- **JSON Response Format**: Structured output for all extraction types

---

## Architecture

1. **PDF or image upload** → OCR service → Markdown text
2. **Extraction Type Selection** → Choose from person, sentiment, company, product, or contact extraction
3. **LangChain Processing** → LLM-enhanced parsing or heuristic fallback based on extraction type
4. **Structured Output** → JSON response with extracted information and confidence scores

---

## Prerequisites

- Python 3.10+
- A MinerU API token for hosted OCR (get one at [MinerU API tokens](https://mineru.net/apiManage/token))
- Optional: an OpenAI-compatible LLM endpoint for enhanced parsing

The hosted model is maintained by MinerU; no local `mineru` Python package or OCR server is required. The service applies its own plan-dependent page limits; check the [official API documentation](https://mineru.net/apiManage/docs).

---

## Quickstart (uv)

Run directly with uv; dependencies are pinned in `pyproject.toml` and `uv.lock`. The current LangChain pins are `langchain==1.4.9`, `langchain-core==1.7.6`, and `langchain-openai==1.7.4`.

Set `MINERU_API_TOKEN` in the process environment before starting the server. `.env.example` is a reference only; the application does not load `.env` files automatically. Do not commit real tokens or API keys.

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

By default, uploaded documents are sent to MinerU for OCR. When `LLM_API_KEY` is configured, OCR text is also sent to the configured LLM endpoint. Requests are synchronous and wait for OCR and extraction to finish, so configure reverse proxies or gateways with suitable request timeouts.

The server accepts PDF, PNG, JPG/JPEG, JP2, WebP, GIF, and BMP uploads up to 200 MiB. The client limits a downloaded MinerU result ZIP to 64 MiB and `full.md` to 16 MiB. MinerU's hosted page limits are separate and vary by service plan.

---

## Usage

### Supported Extraction Types

- **person**: Extract person information (name, job title, company)
- **sentiment**: Analyze sentiment (positive/negative/neutral, confidence, keywords)
- **company_info**: Extract company details (name, industry, address, contact)
- **product_info**: Extract product information (name, price, brand, description)
- **contact_info**: Extract contact details (name, phone, email, address)

### REST API

Start the server:

```powershell
uv run python -m src.server
# API Documentation: http://127.0.0.1:8001/docs
```

#### Get Available Extraction Types

```bash
curl -X GET "http://127.0.0.1:8001/extraction_types"
```

#### Main Extraction Endpoint

```bash
# Extract person information (default)
curl -X POST "http://127.0.0.1:8001/extract" \
  -F "file=@example.jpg"

# Extract sentiment analysis
curl -X POST "http://127.0.0.1:8001/extract?extraction_type=sentiment" \
  -F "file=@example.jpg"

# Extract company information
curl -X POST "http://127.0.0.1:8001/extract?extraction_type=company_info" \
  -F "file=@example.jpg"
```

#### Sample Responses

**Person Information:**
```json
{
  "success": true,
  "data": [{
    "full_name": "Ada Lovelace",
    "job_title": "Software Engineer",
    "company_name": "Example Inc",
    "confidence": 0.67
  }],
  "extraction_type": "person",
  "error_message": null,
  "ocr_text": "# Ada Lovelace\n# Software Engineer\n# Example Inc"
}
```

**Sentiment Analysis:**
```json
{
  "success": true,
  "data": [{
    "sentiment": "positive",
    "confidence_score": 0.8,
    "keywords": ["excellent", "great", "satisfied"],
    "confidence": 0.75
  }],
  "extraction_type": "sentiment",
  "error_message": null,
  "ocr_text": "This product is excellent and great. Very satisfied!"
}
```

#### Legacy Endpoint (Backward Compatibility)

```bash
curl -X POST "http://127.0.0.1:8001/extract_person" \
  -F "file=@example.jpg"
```

---

## Environment Variables

The API server reads exported environment variables; it does not automatically load `.env`. Set at least `MINERU_API_TOKEN` for the default hosted OCR backend.

- `MINERU_API_TOKEN`: token from [MinerU API tokens](https://mineru.net/apiManage/token); never place a real token in the repository
- `MINERU_MODEL_VERSION`: `vlm` (default) or `pipeline`
- `OCR_TIMEOUT_SECONDS`: 30-second timeout for each individual HTTP request
- `MINERU_TASK_TIMEOUT_SECONDS`: 300-second bound for the upload, polling, and result workflow; individual network requests are not guaranteed to stop at this exact wall-clock deadline
- `MINERU_POLL_INTERVAL_SECONDS`: polling interval, default `2` seconds
- `OCR_BACKEND`: `mineru` by default; set to `local` to use the existing local `/file_parse` service
- `OCR_BASE_URL`: local OCR service URL when `OCR_BACKEND=local` (default `http://127.0.0.1:8000`)
- `LLM_MODEL`: default `qwen3:4b-instruct-2507-fp16`
- `LLM_BASE_URL`: default `http://127.0.0.1:11434/v1`
- `LLM_API_KEY`: optional; when empty, heuristic extraction is used
- `LOG_LEVEL`: default `INFO`

Example shell configuration:

```bash
export MINERU_API_TOKEN="paste-your-token-here"
# Optional OpenAI-compatible LLM configuration:
export LLM_BASE_URL="http://127.0.0.1:11434/v1"
export LLM_API_KEY="your-llm-key"
```

To use a local OCR service instead, export `OCR_BACKEND=local` and `OCR_BASE_URL=http://127.0.0.1:8000`. The local endpoint must accept `POST /file_parse` with a multipart `files` field.

---

## API Response

The API returns a JSON response with the following structure:

```json
{
  "success": true,
  "data": [
    {
      "field1": "value1",
      "field2": "value2",
      "confidence": 0.75
    }
  ],
  "extraction_type": "person|sentiment|company_info|product_info|contact_info",
  "error_message": null,
  "ocr_text": "Raw OCR text..."
}
```

The `data` field contains an array of extracted items, where each item's structure depends on the extraction type selected.

---

## Project Structure

```text
MinerU/
  ├─ pyproject.toml
  ├─ uv.lock
  ├─ DEVELOPER_GUIDE.md    # Developer guide (Chinese)
  ├─ DEVELOPER_GUIDE_EN.md # Developer guide (English)
  └─ src/
     ├─ models/           # Data models
     │  ├─ base.py        # Base abstract classes
     │  ├─ person.py      # Person info model
     │  ├─ sentiment.py   # Sentiment analysis model
     │  ├─ company.py     # Company info model
     │  ├─ product.py     # Product info model
     │  └─ contact.py     # Contact info model
     ├─ extractors/       # Extractors
     │  ├─ base.py        # Extractor interface
     │  ├─ langchain_extractor.py  # LangChain implementation
     │  └─ registry.py    # Registry system
     ├─ config/           # Configuration
     │  └─ setup.py       # Default setup
     ├─ plugins/          # Plugin examples
     │  ├─ example_custom_model.py     # Custom model example
     │  └─ example_custom_extractor.py # Custom extractor example
     ├─ server.py         # FastAPI server
     └─ ocr_client.py     # OCR client
```

---

---

## 🔧 Extending the System

### Adding Custom Extraction Types

This project uses a modular architecture that allows you to easily add custom extraction types:

1. **Create Custom Model**: Inherit from `BaseExtractionModel`
2. **Create Custom Extractor**: Implement `BaseExtractor` interface
3. **Register Components**: Use the registry system to add new extraction types

For detailed instructions, see [Developer Guide](DEVELOPER_GUIDE_EN.md)

### Example: Adding Menu Information Extraction

```python
# 1. Define model
class MenuInfo(BaseExtractionModel):
    dish_name: Optional[str] = Field(default=None, description="Dish name")
    price: Optional[str] = Field(default=None, description="Price")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "menu_info"

# 2. Create extractor
class MenuExtractor(BaseExtractor):
    def extract(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        # Implement extraction logic
        pass

# 3. Register
from src.extractors.registry import registry
registry.register_model(MenuInfo)
registry.register_extractor(MenuExtractor())
```

---

## Troubleshooting

- **Hosted OCR setup**: verify `MINERU_API_TOKEN`, model version, quota, and current file/page limits in the [MinerU API documentation](https://mineru.net/apiManage/docs).
- **Local OCR connectivity**: set `OCR_BACKEND=local`; ensure `OCR_BASE_URL` serves `POST /file_parse` with form field `files`.
- **LLM disabled**: set `LLM_*` environment variables in the API server. Heuristic fallback is automatic.
- **API docs**: ensure the server is running and visit `http://127.0.0.1:8001/docs`.
- **Custom extractors not working**: check if models and extractors are properly registered, refer to [Developer Guide](DEVELOPER_GUIDE_EN.md).

---

## License

MIT License

---

## Acknowledgements

- MinerU (OCR)
- LangChain
- FastAPI
