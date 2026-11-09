# Developer Guide

This guide will help you understand the new modular architecture and how to create custom extraction models and extractors.

## 🏗️ New Project Architecture

```
src/
├── models/                 # Data models
│   ├── __init__.py        # Model exports
│   ├── base.py            # Base abstract classes
│   ├── person.py          # Person info model
│   ├── sentiment.py       # Sentiment analysis model
│   ├── company.py         # Company info model
│   ├── product.py         # Product info model
│   └── contact.py         # Contact info model
├── extractors/            # Extractors
│   ├── __init__.py        # Extractor exports
│   ├── base.py            # Extractor base class
│   ├── langchain_extractor.py  # LangChain implementation
│   └── registry.py        # Registry system
├── config/                # Configuration
│   ├── __init__.py        
│   └── setup.py           # Default setup
├── plugins/               # Plugin examples
│   ├── __init__.py        
│   ├── example_custom_model.py      # Custom model example
│   └── example_custom_extractor.py  # Custom extractor example
├── ocr_client.py          # OCR client
└── server.py              # FastAPI server
```

## Running and Service Configuration

The project pins `langchain==1.4.9`, `langchain-core==1.7.6`, and `langchain-openai==1.7.4`. OCR uses the official hosted MinerU v4 API by default; its online models are maintained by the provider, so no local `mineru` package is needed. Export `MINERU_API_TOKEN` before starting the process (get one from the [MinerU token page](https://mineru.net/apiManage/token)). The application does not load `.env` automatically; `.env.example` is a reference, and real credentials must never be committed.

`MINERU_MODEL_VERSION` defaults to `vlm`; `pipeline` is also supported. The client follows the official batch flow: create a task and get an upload URL, upload the document, poll the task, then download the result ZIP and read `full.md`. `OCR_TIMEOUT_SECONDS=30` applies to each HTTP request. `MINERU_TASK_TIMEOUT_SECONDS=300` bounds the workflow wait, but an individual network request is not guaranteed to stop at that exact wall-clock deadline. `MINERU_POLL_INTERVAL_SECONDS` defaults to 2 seconds.

The API accepts PDF, PNG, JPG/JPEG, JP2, WebP, GIF, and BMP uploads up to 200 MiB. Client-side result limits are 64 MiB for the ZIP and 16 MiB for `full.md`. MinerU's hosted page limits vary by plan; check the [official API documentation](https://mineru.net/apiManage/docs). Requests are synchronous and wait for OCR and extraction, so configure reverse proxies or gateways with suitable timeouts. Uploaded documents are sent to MinerU; if an LLM is configured, OCR text is sent to that configured LLM endpoint.

To use a local OCR service, set `OCR_BACKEND=local` and `OCR_BASE_URL` (default `http://127.0.0.1:8000`). It must provide `POST /file_parse` and accept the multipart field `files`.

## 🎯 Core Concepts

### DeepSeek structured extraction contract

- Also pin `langchain-deepseek==1.1.1` and use the official `ChatDeepSeek` integration. Set `DEEPSEEK_API_KEY`; legacy `LLM_API_KEY` is a lower-priority alias. Defaults: `LLM_MODEL=deepseek-flash`, `LLM_BASE_URL=https://api.deepseek.com`, `LLM_MAX_TOKENS=8192`. Clear old local-model names and URLs when migrating.
- Keep single-call extraction, without an Agent. `with_structured_output(method="json_mode", include_raw=True)` requests a JSON object, not native `json_schema` or tool calling. See [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode).
- Instructions, human templates, and model-facing field descriptions are English; extracted values are not translated. The dynamic output schema excludes application-computed `confidence`, requires all business fields (unknown nullable fields use `null`), and forbids extra fields.
- Check raw `finish_reason` and blank content, then strictly validate complete raw JSON with Pydantic. Do not trust a parser that may repair incomplete JSON. Empty, truncated, or invalid output gets only one additional call. SDK network retries are separately configured with `max_retries=2` and a 60-second request timeout.
- No-key mode retains heuristics. Configured-provider or validation failures raise a safe `ExtractionError`, producing API `success=false`, not successful empty or heuristic results. A valid `items=[]` remains successful. Put new model constraints in Pydantic fields; custom validators require extending the dynamic output-model generator as well.

### 1. Base Extraction Model (BaseExtractionModel)

All extraction models should inherit from `BaseExtractionModel`:

```python
from src.models.base import BaseExtractionModel
from pydantic import Field
from typing import Optional

class MyCustomModel(BaseExtractionModel):
    field1: Optional[str] = Field(default=None, description="Field 1")
    field2: Optional[str] = Field(default=None, description="Field 2")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "my_custom_type"
    
    @classmethod
    def get_description(cls) -> str:
        return "My custom model description"
```

### 2. Extractor Interface (BaseExtractor)

All extractors should implement the `BaseExtractor` interface:

```python
from src.extractors.base import BaseExtractor
from src.models.base import BaseExtractionModel
from typing import List, Type

class MyCustomExtractor(BaseExtractor):
    def extract(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        # Implement your extraction logic
        pass
    
    def supports_model(self, model_class: Type[BaseExtractionModel]) -> bool:
        # Return whether this extractor supports the model type
        return model_class.get_extraction_type() == "my_custom_type"
```

### 3. Registry System

Use the registry system to manage models and extractors:

```python
from src.extractors.registry import registry

# Register model
registry.register_model(MyCustomModel)

# Register extractor
registry.register_extractor(MyCustomExtractor())
```

## 📚 Creating Custom Extraction Models

### Step 1: Define the Model

Create your model file in the `src/plugins/` directory:

```python
# src/plugins/my_model.py
from typing import Optional, List
from pydantic import Field
from src.models.base import BaseExtractionModel

class RecipeInfo(BaseExtractionModel):
    """Recipe information model"""
    
    recipe_name: Optional[str] = Field(default=None, description="Recipe name")
    ingredients: Optional[List[str]] = Field(default=None, description="Ingredients list")
    cooking_time: Optional[str] = Field(default=None, description="Cooking time")
    difficulty: Optional[str] = Field(default=None, description="Difficulty level")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "recipe_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "Recipe information (name, ingredients, cooking time, difficulty)"
    
    def calculate_confidence(self) -> float:
        """Custom confidence calculation"""
        confidence = super().calculate_confidence()
        
        # Boost confidence if ingredients list exists
        if self.ingredients and len(self.ingredients) > 0:
            confidence = min(1.0, confidence + 0.1)
        
        return confidence
```

### Step 2: Create the Extractor

```python
# src/plugins/my_extractor.py
import re
from typing import List, Type
from src.extractors.base import BaseExtractor
from src.models.base import BaseExtractionModel
from .my_model import RecipeInfo

class RecipeExtractor(BaseExtractor):
    """Recipe information extractor"""
    
    def __init__(self):
        self.time_pattern = r'\d+\s*(?:minutes?|mins?|hours?|hrs?)'
        self.difficulty_keywords = ['easy', 'medium', 'hard', 'simple', 'complex']
    
    def extract(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        if model_class != RecipeInfo:
            return []
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        recipe_name = None
        ingredients = []
        cooking_time = None
        difficulty = None
        
        for line in lines:
            # Find cooking time
            time_match = re.search(self.time_pattern, line, re.IGNORECASE)
            if time_match and not cooking_time:
                cooking_time = time_match.group()
            
            # Find difficulty
            for keyword in self.difficulty_keywords:
                if keyword.lower() in line.lower():
                    difficulty = keyword
                    break
            
            # Find ingredients (lines containing common food measurement keywords)
            food_keywords = ['cup', 'tsp', 'tbsp', 'oz', 'lb', 'gram', 'kg']
            if any(keyword in line.lower() for keyword in food_keywords):
                ingredients.append(line)
            elif not recipe_name and len(line) > 2:
                recipe_name = line
        
        recipe = model_class(
            recipe_name=recipe_name,
            ingredients=ingredients,
            cooking_time=cooking_time,
            difficulty=difficulty
        )
        
        return [recipe]
    
    def supports_model(self, model_class: Type[BaseExtractionModel]) -> bool:
        return model_class == RecipeInfo
```

### Step 3: Register and Use

```python
# Register during application startup (can be added to src/config/setup.py)
from src.extractors.registry import registry
from src.plugins.my_model import RecipeInfo
from src.plugins.my_extractor import RecipeExtractor

def setup_custom_extractors():
    registry.register_model(RecipeInfo)
    registry.register_extractor(RecipeExtractor())

# Then you can use it
result = registry.extract(text, "recipe_info")
```

## 🔌 Plugin System Usage

### Method 1: Direct Registration

```python
from src.extractors.registry import registry

# Import your custom model and extractor
from src.plugins.my_model import RecipeInfo
from src.plugins.my_extractor import RecipeExtractor

# Register
registry.register_model(RecipeInfo)
registry.register_extractor(RecipeExtractor())
```

### Method 2: Batch Loading

```python
# src/plugins/load_custom.py
from src.extractors.registry import registry
from .my_model import RecipeInfo
from .my_extractor import RecipeExtractor

def load_custom_plugins():
    """Load all custom plugins"""
    registry.register_model(RecipeInfo)
    registry.register_extractor(RecipeExtractor())
    print("Custom plugins loaded successfully")

# Call in src/config/setup.py
from src.plugins.load_custom import load_custom_plugins

def setup_default_extractors():
    # ... existing code ...
    
    # Load custom plugins
    load_custom_plugins()
```

## 🧪 Testing Your Extractor

```python
# test_my_extractor.py
from src.plugins.my_model import RecipeInfo
from src.plugins.my_extractor import RecipeExtractor

def test_recipe_extraction():
    extractor = RecipeExtractor()
    
    test_text = """
    Chocolate Chip Cookies
    2 cups flour
    1 cup sugar
    1 tsp vanilla
    Cooking time: 25 minutes
    Difficulty: Easy
    """
    
    results = extractor.extract(test_text, RecipeInfo)
    
    assert len(results) == 1
    recipe = results[0]
    assert recipe.recipe_name == "Chocolate Chip Cookies"
    assert recipe.cooking_time == "25 minutes"
    assert recipe.difficulty == "Easy"
    assert len(recipe.ingredients) >= 2
    
    print("Test passed!")

if __name__ == "__main__":
    test_recipe_extraction()
```

## 🚀 Best Practices

### 1. Model Design
- Inherit from `BaseExtractionModel`
- Provide clear field descriptions
- Implement reasonable confidence calculation
- Use optional fields to avoid strict requirements

### 2. Extractor Design
- Implement the `BaseExtractor` interface
- Provide heuristic fallback logic
- Handle edge cases gracefully
- Return meaningful error information

### 3. Error Handling
- Catch exceptions in extractors
- Return empty lists instead of throwing exceptions
- Log detailed error messages

### 4. Performance Optimization
- Cache compiled regular expressions
- Avoid repeated calculations
- Use generators for large data processing

## 🔍 Debugging Tips

### 1. Enable Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Test Individual Components
```python
# Test model separately
model = RecipeInfo(recipe_name="Test", cooking_time="10 minutes")
print(model.model_dump())

# Test extractor separately
extractor = RecipeExtractor()
result = extractor.extract("test text", RecipeInfo)
```

### 3. Verify Registration Status
```python
from src.extractors.registry import registry

# Check registered models
print("Registered extraction types:", [t["type"] for t in registry.get_supported_types()])

# Check if specific model is supported
print("Supports RecipeInfo:", registry.get_model_class("recipe_info") is not None)
```

## 🌐 Internationalization

### Supporting Multiple Languages

You can create language-specific extractors:

```python
class RecipeExtractorEN(RecipeExtractor):
    def __init__(self):
        super().__init__()
        self.difficulty_keywords = ['easy', 'medium', 'hard', 'simple', 'complex']

class RecipeExtractorZH(RecipeExtractor):
    def __init__(self):
        super().__init__()
        self.difficulty_keywords = ['简单', '中等', '困难', '容易', '复杂']
        self.time_pattern = r'\d+\s*[分钟小时]'
```

## 📖 API Integration

### Using Custom Models with the API

Once registered, your custom models are automatically available via the REST API:

```bash
# Get available extraction types
curl -X GET "http://127.0.0.1:8001/extraction_types"

# Use your custom extractor
curl -X POST "http://127.0.0.1:8001/extract?extraction_type=recipe_info" \
  -F "file=@recipe_image.jpg"
```

## 🔄 Migration Guide

### From Old Architecture to New

If you're migrating from the old monolithic structure:

1. **Extract Models**: Move model definitions to `src/models/`
2. **Extract Logic**: Move extraction logic to `src/extractors/`
3. **Register Components**: Use the registry system
4. **Update Imports**: Update import statements

```python
# Old way
from server import Person, LangChainExtractor

# New way
from src.models.person import Person
from src.extractors.langchain_extractor import LangChainExtractor
from src.extractors.registry import registry
```

This new architecture provides:
- ✅ **Low Coupling**: Each component is independent
- ✅ **High Cohesion**: Related functionality is organized together
- ✅ **Extensibility**: Easy to add new extraction types
- ✅ **Testability**: Each component can be tested independently
- ✅ **Backward Compatibility**: Existing APIs continue to work

Now other developers can easily create custom extractors for their specific use cases without modifying the core code!
