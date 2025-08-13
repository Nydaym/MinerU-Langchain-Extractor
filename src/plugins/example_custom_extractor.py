"""自定义抽取器示例

这个文件展示了如何创建自定义的抽取器。
用户可以参考这个示例来创建自己的抽取逻辑。
"""

import re
from typing import List, Type
from ..extractors.base import BaseExtractor
from ..models.base import BaseExtractionModel
from .example_custom_model import MenuInfo


class SimpleRegexExtractor(BaseExtractor):
    """简单的基于正则表达式的抽取器示例
    
    这个示例展示了如何创建一个简单的抽取器，
    使用正则表达式来抽取特定格式的信息。
    """
    
    def __init__(self):
        """初始化抽取器"""
        # 定义各种正则表达式模式
        self.patterns = {
            "price": r'[¥$￥]\s*\d+(?:\.\d{2})?|\d+(?:\.\d{2})?\s*[元块]',
            "phone": r'1[3-9]\d{9}|0\d{2,3}-?\d{7,8}',
            "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "spicy": r'[不无]?辣|微辣|中辣|特辣|变态辣'
        }
    
    def extract(
        self, 
        text: str, 
        model_class: Type[BaseExtractionModel]
    ) -> List[BaseExtractionModel]:
        """使用正则表达式抽取信息"""
        
        if model_class == MenuInfo:
            return self._extract_menu_info(text, model_class)
        else:
            # 对于不支持的模型，返回空列表
            return []
    
    def supports_model(self, model_class: Type[BaseExtractionModel]) -> bool:
        """检查是否支持指定模型"""
        # 这个示例抽取器只支持 MenuInfo 模型
        return model_class == MenuInfo
    
    def _extract_menu_info(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        """抽取菜单信息"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 简单的启发式规则
        dish_name = None
        price = None
        description = None
        spicy_level = None
        
        for line in lines:
            # 查找价格
            price_match = re.search(self.patterns["price"], line)
            if price_match and not price:
                price = price_match.group()
            
            # 查找辣度
            spicy_match = re.search(self.patterns["spicy"], line)
            if spicy_match:
                spicy_level = spicy_match.group()
            
            # 如果不包含价格和特殊符号，可能是菜品名称
            if not price_match and not dish_name and len(line) > 2:
                dish_name = line
            elif dish_name and not description and len(line) > 5:
                description = line
        
        # 创建模型实例
        menu_item = model_class(
            dish_name=dish_name,
            price=price,
            description=description,
            spicy_level=spicy_level
        )
        
        return [menu_item]


# 使用示例：
# 
# 1. 在应用启动时注册：
#    from src.extractors.registry import registry
#    from src.plugins.example_custom_model import MenuInfo
#    from src.plugins.example_custom_extractor import SimpleRegexExtractor
#    
#    registry.register_model(MenuInfo)
#    registry.register_extractor(SimpleRegexExtractor())
#
# 2. 然后就可以使用了：
#    result = registry.extract(text, "menu_info")
