# 通用 OCR 信息抽取器

[English](README.md) | [简体中文](README.zh-CN.md)

通用信息抽取系统，使用 OCR 和 LangChain 从图片中抽取各种类型的信息。支持多种抽取类型，包括人员信息、情感分析、公司详情、产品信息和联系方式。提供 FastAPI REST API 服务进行图片处理。

---

## 特性

- **通用信息抽取**：支持多种抽取类型（人员、情感、公司、产品、联系方式）
- **OCR 集成**：对接本地 MinerU OCR 服务（默认 `http://127.0.0.1:8000/file_parse`）
- **LangChain 解析**：针对每种抽取类型提供 LLM 增强模式与启发式回退
- **REST API**：RESTful 端点支持灵活的抽取类型选择
- **向后兼容**：保留旧版接口的功能
- **JSON 响应格式**：所有抽取类型的结构化输出

---

## 架构

1. **图片上传** → OCR 服务 → Markdown 文本（`md_content`）
2. **抽取类型选择** → 从人员、情感、公司、产品或联系方式抽取中选择
3. **LangChain 处理** → 基于抽取类型进行 LLM 增强解析或启发式回退
4. **结构化输出** → 包含抽取信息和置信度的 JSON 响应

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

### 支持的抽取类型

- **person**：抽取人员信息（姓名、职位、公司）
- **sentiment**：情感分析（积极/消极/中性、置信度、关键词）
- **company_info**：抽取公司详情（名称、行业、地址、联系方式）
- **product_info**：抽取产品信息（名称、价格、品牌、描述）
- **contact_info**：抽取联系详情（姓名、电话、邮箱、地址）

### REST API

启动服务：

```powershell
uv run python -m src.server
# API 文档: http://127.0.0.1:8001/docs
```

#### 获取可用的抽取类型

```bash
curl -X GET "http://127.0.0.1:8001/extraction_types"
```

#### 主要抽取端点

```bash
# 抽取人员信息（默认）
curl -X POST "http://127.0.0.1:8001/extract" \
  -F "file=@example.jpg"

# 情感分析
curl -X POST "http://127.0.0.1:8001/extract?extraction_type=sentiment" \
  -F "file=@example.jpg"

# 抽取公司信息
curl -X POST "http://127.0.0.1:8001/extract?extraction_type=company_info" \
  -F "file=@example.jpg"
```

#### 响应示例

**人员信息：**
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

**情感分析：**
```json
{
  "success": true,
  "data": [{
    "sentiment": "positive",
    "confidence_score": 0.8,
    "keywords": ["优秀", "很好", "满意"],
    "confidence": 0.75
  }],
  "extraction_type": "sentiment",
  "error_message": null,
  "ocr_text": "这个产品很优秀，质量很好。非常满意！"
}
```

#### 旧版端点（向后兼容）

```bash
curl -X POST "http://127.0.0.1:8001/extract_person" \
  -F "file=@example.jpg"
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
  "data": [
    {
      "字段1": "值1",
      "字段2": "值2",
      "confidence": 0.75
    }
  ],
  "extraction_type": "person|sentiment|company_info|product_info|contact_info",
  "error_message": null,
  "ocr_text": "原始 OCR 文本..."
}
```

`data` 字段包含抽取项的数组，每个项的结构取决于选择的抽取类型。

---

## 项目结构

```text
MinerU/
  ├─ pyproject.toml
  ├─ uv.lock
  ├─ DEVELOPER_GUIDE.md    # 开发者指南
  └─ src/
     ├─ models/           # 数据模型
     │  ├─ base.py        # 基础抽象类
     │  ├─ person.py      # 人员信息模型
     │  ├─ sentiment.py   # 情感分析模型
     │  ├─ company.py     # 公司信息模型
     │  ├─ product.py     # 产品信息模型
     │  └─ contact.py     # 联系信息模型
     ├─ extractors/       # 抽取器
     │  ├─ base.py        # 抽取器基类
     │  ├─ langchain_extractor.py  # LangChain实现
     │  └─ registry.py    # 注册系统
     ├─ config/           # 配置
     │  └─ setup.py       # 默认设置
     ├─ plugins/          # 插件示例
     │  ├─ example_custom_model.py     # 自定义模型示例
     │  └─ example_custom_extractor.py # 自定义抽取器示例
     ├─ server.py         # FastAPI 服务器
     └─ ocr_client.py     # OCR 客户端
```

---

---

## 🔧 扩展开发

### 添加自定义抽取类型

本项目采用模块化架构，您可以轻松添加自定义的抽取类型：

1. **创建自定义模型**：继承 `BaseExtractionModel`
2. **创建自定义抽取器**：实现 `BaseExtractor` 接口  
3. **注册组件**：使用注册系统添加新的抽取类型

详细指南请参考 `DEVELOPER_GUIDE.md`

### 示例：添加菜单信息抽取

```python
# 1. 定义模型
class MenuInfo(BaseExtractionModel):
    dish_name: Optional[str] = Field(default=None, description="菜品名称")
    price: Optional[str] = Field(default=None, description="价格")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "menu_info"

# 2. 创建抽取器
class MenuExtractor(BaseExtractor):
    def extract(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        # 实现抽取逻辑
        pass

# 3. 注册
from src.extractors.registry import registry
registry.register_model(MenuInfo)
registry.register_extractor(MenuExtractor())
```

---

## 故障排查

- **无法连接 OCR**：确认 MinerU 服务已启动在 `http://127.0.0.1:8000`；检查 `POST /file_parse` 是否接受 `files` 字段。
- **LLM 未启用**：需在 API 服务端设置 `LLM_*` 环境变量。未设置时将自动回退到启发式解析。
- **API 文档不可访问**：确认服务已运行并访问 `http://127.0.0.1:8001/docs`。
- **自定义抽取器未生效**：检查模型和抽取器是否正确注册，参考 `DEVELOPER_GUIDE.md`。

---

## 许可

MIT License

---

## 致谢

- MinerU（OCR）
- LangChain
- FastAPI
