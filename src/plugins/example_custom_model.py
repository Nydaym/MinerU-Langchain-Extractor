"""自定义模型示例

这个文件展示了如何创建自定义的抽取模型。
用户可以参考这个示例来创建自己的模型。
"""

from typing import Optional
from pydantic import Field
from ..models.base import BaseExtractionModel


class MenuInfo(BaseExtractionModel):
    """菜单信息模型示例
    
    这是一个示例模型，展示如何创建自定义的抽取模型。
    用户可以参考这个示例来创建适合自己需求的模型。
    """
    
    dish_name: Optional[str] = Field(default=None, description="菜品名称")
    price: Optional[str] = Field(default=None, description="价格")
    description: Optional[str] = Field(default=None, description="菜品描述")
    category: Optional[str] = Field(default=None, description="菜品分类")
    spicy_level: Optional[str] = Field(default=None, description="辣度等级")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "menu_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "菜单信息（菜品、价格、描述、分类）"
    
    def calculate_confidence(self) -> float:
        """自定义置信度计算
        
        可以根据特定业务逻辑来计算置信度。
        例如，如果菜品名称和价格都存在，置信度更高。
        """
        confidence = super().calculate_confidence()
        
        # 如果同时有菜品名称和价格，额外加分
        if self.dish_name and self.price:
            confidence = min(1.0, confidence + 0.2)
        
        return confidence


# 使用示例：
# 1. 创建自定义抽取器类，继承自 BaseExtractor
# 2. 在抽取器中实现针对菜单的特殊逻辑
# 3. 在应用启动时注册模型和抽取器：
#    from src.extractors.registry import registry
#    registry.register_model(MenuInfo)
#    registry.register_extractor(CustomMenuExtractor())
