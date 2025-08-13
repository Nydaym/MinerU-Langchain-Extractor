"""基础模型定义"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BaseExtractionModel(BaseModel, ABC):
    """抽取模型的基类
    
    所有抽取模型都应该继承此类，并实现相应的方法。
    这样可以确保一致的接口和行为。
    """
    
    confidence: float = Field(default=0.0, description="抽取置信度", ge=0.0, le=1.0)
    
    @classmethod
    @abstractmethod
    def get_extraction_type(cls) -> str:
        """返回抽取类型标识符"""
        pass
    
    @classmethod
    @abstractmethod
    def get_description(cls) -> str:
        """返回抽取类型的描述"""
        pass
    
    def calculate_confidence(self) -> float:
        """计算抽取置信度
        
        默认实现：根据非空字段数量计算置信度
        子类可以重写此方法以实现自定义的置信度计算逻辑
        """
        filled_fields = 0
        total_fields = len(self.__fields__) - 1  # 减去confidence字段
        
        for field_name in self.__fields__:
            if field_name != 'confidence':
                value = getattr(self, field_name, None)
                if value is not None and str(value).strip():
                    filled_fields += 1
        
        return filled_fields / total_fields if total_fields > 0 else 0.0
    
    def update_confidence(self):
        """更新置信度"""
        self.confidence = self.calculate_confidence()


class ExtractionResponse(BaseModel):
    """API响应模型"""
    
    success: bool = Field(description="处理是否成功")
    data: Optional[List[Dict[str, Any]]] = Field(default=None, description="抽取的信息")
    extraction_type: Optional[str] = Field(default=None, description="抽取类型")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    ocr_text: Optional[str] = Field(default=None, description="原始OCR文本")
