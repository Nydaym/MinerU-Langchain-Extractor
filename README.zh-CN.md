# 通用 OCR 信息抽取器

📚 文档语言: [English](README.md) | [简体中文](README.zh-CN.md)  
📖 开发者指南: [中文版](DEVELOPER_GUIDE.md) | [English](DEVELOPER_GUIDE_EN.md)

通用信息抽取系统，使用 OCR 和 LangChain 从 PDF 与图片中抽取各种类型的信息。支持人员信息、情感分析、公司详情、产品信息和联系方式，并提供 FastAPI REST API。

---

## 特性

- **通用信息抽取**：支持多种抽取类型（人员、情感、公司、产品、联系方式）
- **OCR 集成**：默认使用 MinerU 官方在线 API，也可选择已有的本地 OCR 服务
- **LangChain 解析**：针对每种抽取类型提供 LLM 增强模式与启发式回退
- **REST API**：RESTful 端点支持灵活的抽取类型选择
- **向后兼容**：保留旧版接口的功能
- **JSON 响应格式**：所有抽取类型的结构化输出

---

## 架构

1. **上传 PDF 或图片** → OCR 服务 → Markdown 文本
2. **抽取类型选择** → 从人员、情感、公司、产品或联系方式抽取中选择
3. **LangChain 处理** → 基于抽取类型进行 LLM 增强解析或启发式回退
4. **结构化输出** → 包含抽取信息和置信度的 JSON 响应

---

## 先决条件

- Python 3.10+
- MinerU API Token（可在 [MinerU API Token 页面](https://mineru.net/apiManage/token)获取）
- 可选：OpenAI 兼容的 LLM 接口

默认在线模型由 MinerU 提供和维护；无需安装本地 `mineru` Python 包或启动 OCR 服务。在线服务的页数限制取决于服务方案，请查看 [MinerU 官方 API 文档](https://mineru.net/apiManage/docs)。

---

## 快速开始（使用 uv）

使用 uv 直接运行；依赖版本由 `pyproject.toml` 和 `uv.lock` 固定。当前 LangChain 版本为 `langchain==1.4.9`、`langchain-core==1.7.6`、`langchain-openai==1.7.4`。

启动前请在进程环境中设置 `MINERU_API_TOKEN`。`.env.example` 仅供参考，程序不会自动加载 `.env` 文件。不要将真实 Token 或 API Key 提交到仓库。

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

默认情况下，上传的文档会发送给 MinerU 进行 OCR。配置 `LLM_API_KEY` 后，OCR 文本还会发送到所配置的 LLM 服务端点。API 请求为同步处理，会等待 OCR 和信息抽取完成；请为反向代理或网关设置足够的请求超时。

服务接受最大 200 MiB 的 PDF、PNG、JPG/JPEG、JP2、WebP、GIF 和 BMP 文件。客户端对下载结果 ZIP 限制为 64 MiB，对 `full.md` 限制为 16 MiB。MinerU 在线服务另有按方案而异的页数限制。

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

API 服务读取已导出的环境变量，不会自动加载 `.env`。默认在线 OCR 至少需要 `MINERU_API_TOKEN`。

- `MINERU_API_TOKEN`：从 [MinerU API Token 页面](https://mineru.net/apiManage/token)获取；不要将真实 Token 放入代码仓库
- `MINERU_MODEL_VERSION`：`vlm`（默认）或 `pipeline`
- `OCR_TIMEOUT_SECONDS`：每个 HTTP 请求的超时，默认 30 秒
- `MINERU_TASK_TIMEOUT_SECONDS`：上传、轮询和下载流程的 300 秒时限；单个网络请求不保证严格在该墙钟时限结束
- `MINERU_POLL_INTERVAL_SECONDS`：轮询间隔，默认 2 秒
- `OCR_BACKEND`：默认 `mineru`；设为 `local` 使用现有本地 `/file_parse` 服务
- `OCR_BASE_URL`：`OCR_BACKEND=local` 时的本地 OCR 服务地址，默认 `http://127.0.0.1:8000`
- `LLM_MODEL`：默认 `qwen3:4b-instruct-2507-fp16`
- `LLM_BASE_URL`：默认 `http://127.0.0.1:11434/v1`
- `LLM_API_KEY`：可选；留空时使用启发式抽取
- `LOG_LEVEL`：默认 `INFO`

Shell 配置示例：

```bash
export MINERU_API_TOKEN="在此填入 Token"
# 可选的 OpenAI 兼容 LLM 配置：
export LLM_BASE_URL="http://127.0.0.1:11434/v1"
export LLM_API_KEY="你的 LLM Key"
```

如需本地 OCR，请导出 `OCR_BACKEND=local` 和 `OCR_BASE_URL=http://127.0.0.1:8000`。本地服务必须支持 `POST /file_parse` 和 multipart 字段 `files`。

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
  ├─ DEVELOPER_GUIDE.md    # 开发者指南（中文）
  ├─ DEVELOPER_GUIDE_EN.md # 开发者指南（英文）
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

详细指南请参考 [开发者指南](DEVELOPER_GUIDE.md)

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

- **在线 OCR 配置**：检查 `MINERU_API_TOKEN`、模型版本、额度以及 [MinerU API 文档](https://mineru.net/apiManage/docs)中的当前文件和页数限制。
- **本地 OCR 连接**：设置 `OCR_BACKEND=local`，并确认 `OCR_BASE_URL` 提供 `POST /file_parse` 和 `files` 表单字段。
- **LLM 未启用**：需在 API 服务端设置 `LLM_*` 环境变量。未设置时将自动回退到启发式解析。
- **API 文档不可访问**：确认服务已运行并访问 `http://127.0.0.1:8001/docs`。
- **自定义抽取器未生效**：检查模型和抽取器是否正确注册，参考 [开发者指南](DEVELOPER_GUIDE.md)。

---

## 许可

MIT License

---

## 致谢

- MinerU（OCR）
- LangChain
- FastAPI
