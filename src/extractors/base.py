"""基础抽取器接口"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type
from ..models.base import BaseExtractionModel


class BaseExtractor(ABC):
    """抽取器基类
    
    定义了所有抽取器必须实现的接口。
    这样可以确保不同的抽取器实现具有一致的API。
    """
    
    @abstractmethod
    def extract(
        self, 
        text: str, 
        model_class: Type[BaseExtractionModel]
    ) -> List[BaseExtractionModel]:
        """抽取信息
        
        Args:
            text: 要抽取的文本
            model_class: 抽取模型类
            
        Returns:
            抽取结果列表
        """
        pass
    
    @abstractmethod
    def supports_model(self, model_class: Type[BaseExtractionModel]) -> bool:
        """检查是否支持指定的模型类型
        
        Args:
            model_class: 模型类
            
        Returns:
            是否支持该模型
        """
        pass
