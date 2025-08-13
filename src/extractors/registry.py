"""抽取器注册系统"""

from typing import Dict, Type, List, Optional
from ..models.base import BaseExtractionModel
from .base import BaseExtractor


class ExtractorRegistry:
    """抽取器注册中心
    
    管理所有可用的抽取器和模型类型。
    支持动态注册新的抽取器和模型。
    """
    
    def __init__(self):
        self._models: Dict[str, Type[BaseExtractionModel]] = {}
        self._extractors: List[BaseExtractor] = []
    
    def register_model(self, model_class: Type[BaseExtractionModel]) -> None:
        """注册模型类型
        
        Args:
            model_class: 模型类
        """
        extraction_type = model_class.get_extraction_type()
        self._models[extraction_type] = model_class
        print(f"已注册模型类型: {extraction_type} -> {model_class.__name__}")
    
    def register_extractor(self, extractor: BaseExtractor) -> None:
        """注册抽取器
        
        Args:
            extractor: 抽取器实例
        """
        self._extractors.append(extractor)
        print(f"已注册抽取器: {extractor.__class__.__name__}")
    
    def get_model_class(self, extraction_type: str) -> Optional[Type[BaseExtractionModel]]:
        """获取模型类
        
        Args:
            extraction_type: 抽取类型
            
        Returns:
            模型类，如果不存在则返回None
        """
        return self._models.get(extraction_type)
    
    def get_supported_types(self) -> List[Dict[str, str]]:
        """获取支持的抽取类型列表
        
        Returns:
            抽取类型信息列表
        """
        return [
            {
                "type": extraction_type,
                "description": model_class.get_description()
            }
            for extraction_type, model_class in self._models.items()
        ]
    
    def find_extractor(self, model_class: Type[BaseExtractionModel]) -> Optional[BaseExtractor]:
        """查找支持指定模型的抽取器
        
        Args:
            model_class: 模型类
            
        Returns:
            抽取器实例，如果找不到则返回None
        """
        for extractor in self._extractors:
            if extractor.supports_model(model_class):
                return extractor
        return None
    
    def extract(
        self, 
        text: str, 
        extraction_type: str
    ) -> List[BaseExtractionModel]:
        """执行信息抽取
        
        Args:
            text: 要抽取的文本
            extraction_type: 抽取类型
            
        Returns:
            抽取结果列表
        """
        model_class = self.get_model_class(extraction_type)
        if not model_class:
            raise ValueError(f"不支持的抽取类型: {extraction_type}")
        
        extractor = self.find_extractor(model_class)
        if not extractor:
            raise ValueError(f"找不到支持 {extraction_type} 的抽取器")
        
        return extractor.extract(text, model_class)


# 全局注册实例
registry = ExtractorRegistry()
