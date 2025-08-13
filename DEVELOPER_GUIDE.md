# 开发者指南

本指南将帮助您了解新的模块化架构，以及如何创建自定义的抽取模型和抽取器。

## 🏗️ 新的项目架构

```
src/
├── models/                 # 数据模型
│   ├── __init__.py        # 模型导出
│   ├── base.py            # 基础抽象类
│   ├── person.py          # 人员信息模型
│   ├── sentiment.py       # 情感分析模型
│   ├── company.py         # 公司信息模型
│   ├── product.py         # 产品信息模型
│   └── contact.py         # 联系信息模型
├── extractors/            # 抽取器
│   ├── __init__.py        # 抽取器导出
│   ├── base.py            # 抽取器基类
│   ├── langchain_extractor.py  # LangChain实现
│   └── registry.py        # 注册系统
├── config/                # 配置
│   ├── __init__.py        
│   └── setup.py           # 默认设置
├── plugins/               # 插件示例
│   ├── __init__.py        
│   ├── example_custom_model.py      # 自定义模型示例
│   └── example_custom_extractor.py  # 自定义抽取器示例
├── ocr_client.py          # OCR客户端
└── server.py              # FastAPI服务器
```

## 🎯 核心概念

### 1. 基础抽取模型 (BaseExtractionModel)

所有抽取模型都应该继承 `BaseExtractionModel`：

```python
from src.models.base import BaseExtractionModel
from pydantic import Field
from typing import Optional

class MyCustomModel(BaseExtractionModel):
    field1: Optional[str] = Field(default=None, description="字段1")
    field2: Optional[str] = Field(default=None, description="字段2")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "my_custom_type"
    
    @classmethod
    def get_description(cls) -> str:
        return "我的自定义模型描述"
```

### 2. 抽取器接口 (BaseExtractor)

所有抽取器都应该实现 `BaseExtractor` 接口：

```python
from src.extractors.base import BaseExtractor
from src.models.base import BaseExtractionModel
from typing import List, Type

class MyCustomExtractor(BaseExtractor):
    def extract(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        # 实现您的抽取逻辑
        pass
    
    def supports_model(self, model_class: Type[BaseExtractionModel]) -> bool:
        # 返回是否支持该模型类型
        return model_class.get_extraction_type() == "my_custom_type"
```

### 3. 注册系统

使用注册系统来管理模型和抽取器：

```python
from src.extractors.registry import registry

# 注册模型
registry.register_model(MyCustomModel)

# 注册抽取器
registry.register_extractor(MyCustomExtractor())
```

## 📚 创建自定义抽取模型

### 步骤 1：定义模型

在 `src/plugins/` 目录下创建您的模型文件：

```python
# src/plugins/my_model.py
from typing import Optional, List
from pydantic import Field
from src.models.base import BaseExtractionModel

class RecipeInfo(BaseExtractionModel):
    """食谱信息模型"""
    
    recipe_name: Optional[str] = Field(default=None, description="食谱名称")
    ingredients: Optional[List[str]] = Field(default=None, description="食材列表")
    cooking_time: Optional[str] = Field(default=None, description="烹饪时间")
    difficulty: Optional[str] = Field(default=None, description="难度等级")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "recipe_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "食谱信息（名称、食材、烹饪时间、难度）"
    
    def calculate_confidence(self) -> float:
        """自定义置信度计算"""
        confidence = super().calculate_confidence()
        
        # 如果有食材列表，提高置信度
        if self.ingredients and len(self.ingredients) > 0:
            confidence = min(1.0, confidence + 0.1)
        
        return confidence
```

### 步骤 2：创建抽取器

```python
# src/plugins/my_extractor.py
import re
from typing import List, Type
from src.extractors.base import BaseExtractor
from src.models.base import BaseExtractionModel
from .my_model import RecipeInfo

class RecipeExtractor(BaseExtractor):
    """食谱信息抽取器"""
    
    def __init__(self):
        self.time_pattern = r'\d+\s*[分钟小时]'
        self.difficulty_keywords = ['简单', '中等', '困难', '容易', '复杂']
    
    def extract(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        if model_class != RecipeInfo:
            return []
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        recipe_name = None
        ingredients = []
        cooking_time = None
        difficulty = None
        
        for line in lines:
            # 查找烹饪时间
            time_match = re.search(self.time_pattern, line)
            if time_match and not cooking_time:
                cooking_time = time_match.group()
            
            # 查找难度
            for keyword in self.difficulty_keywords:
                if keyword in line:
                    difficulty = keyword
                    break
            
            # 查找食材（包含常见食材关键词的行）
            food_keywords = ['克', '个', '根', '片', '勺', '杯']
            if any(keyword in line for keyword in food_keywords):
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

### 步骤 3：注册和使用

```python
# 在应用启动时注册（可以在 src/config/setup.py 中添加）
from src.extractors.registry import registry
from src.plugins.my_model import RecipeInfo
from src.plugins.my_extractor import RecipeExtractor

def setup_custom_extractors():
    registry.register_model(RecipeInfo)
    registry.register_extractor(RecipeExtractor())

# 然后就可以使用了
result = registry.extract(text, "recipe_info")
```

## 🔌 插件系统使用

### 方法1：直接注册

```python
from src.extractors.registry import registry

# 导入您的自定义模型和抽取器
from src.plugins.my_model import RecipeInfo
from src.plugins.my_extractor import RecipeExtractor

# 注册
registry.register_model(RecipeInfo)
registry.register_extractor(RecipeExtractor())
```

### 方法2：批量加载

```python
# src/plugins/load_custom.py
from src.extractors.registry import registry
from .my_model import RecipeInfo
from .my_extractor import RecipeExtractor

def load_custom_plugins():
    """加载所有自定义插件"""
    registry.register_model(RecipeInfo)
    registry.register_extractor(RecipeExtractor())
    print("自定义插件加载完成")

# 在 src/config/setup.py 中调用
from src.plugins.load_custom import load_custom_plugins

def setup_default_extractors():
    # ... 现有代码 ...
    
    # 加载自定义插件
    load_custom_plugins()
```

## 🧪 测试您的抽取器

```python
# test_my_extractor.py
from src.plugins.my_model import RecipeInfo
from src.plugins.my_extractor import RecipeExtractor

def test_recipe_extraction():
    extractor = RecipeExtractor()
    
    test_text = """
    红烧肉
    猪肉 500克
    生抽 2勺
    老抽 1勺
    烹饪时间: 30分钟
    难度: 简单
    """
    
    results = extractor.extract(test_text, RecipeInfo)
    
    assert len(results) == 1
    recipe = results[0]
    assert recipe.recipe_name == "红烧肉"
    assert recipe.cooking_time == "30分钟"
    assert recipe.difficulty == "简单"
    assert len(recipe.ingredients) >= 2
    
    print("测试通过！")

if __name__ == "__main__":
    test_recipe_extraction()
```

## 🚀 最佳实践

### 1. 模型设计
- 继承 `BaseExtractionModel`
- 提供清晰的字段描述
- 实现合理的置信度计算
- 使用可选字段，避免强制要求

### 2. 抽取器设计
- 实现 `BaseExtractor` 接口
- 提供启发式回退逻辑
- 处理边界情况
- 返回有意义的错误信息

### 3. 错误处理
- 在抽取器中捕获异常
- 返回空列表而不是抛出异常
- 记录详细的错误日志

### 4. 性能优化
- 缓存编译的正则表达式
- 避免重复计算
- 使用生成器处理大量数据

## 🔍 调试技巧

### 1. 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 测试单个组件
```python
# 单独测试模型
model = RecipeInfo(recipe_name="测试", cooking_time="10分钟")
print(model.model_dump())

# 单独测试抽取器
extractor = RecipeExtractor()
result = extractor.extract("测试文本", RecipeInfo)
```

### 3. 验证注册状态
```python
from src.extractors.registry import registry

# 查看已注册的模型
print("已注册的抽取类型:", [t["type"] for t in registry.get_supported_types()])

# 查看是否支持特定模型
print("支持RecipeInfo:", registry.get_model_class("recipe_info") is not None)
```

这种新的架构提供了：
- ✅ **低耦合**：每个组件都是独立的
- ✅ **高内聚**：相关功能组织在一起
- ✅ **可扩展**：轻松添加新的抽取类型
- ✅ **可测试**：每个组件都可以独立测试
- ✅ **向后兼容**：现有API继续工作

现在其他开发者可以轻松地为他们的特定用例创建自定义抽取器，而无需修改核心代码！
