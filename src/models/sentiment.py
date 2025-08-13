"""情感分析模型"""

from typing import Optional, List
from pydantic import Field
from .base import BaseExtractionModel


class Sentiment(BaseExtractionModel):
    """情感分析模型"""
    
    sentiment: Optional[str] = Field(default=None, description="情感倾向 (positive/negative/neutral)")
    confidence_score: float = Field(default=0.0, description="情感置信度分数", ge=0.0, le=1.0)
    keywords: Optional[List[str]] = Field(default=None, description="关键词")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "sentiment"
    
    @classmethod
    def get_description(cls) -> str:
        return "情感分析（情感倾向、置信度、关键词）"
    
    def calculate_confidence(self) -> float:
        """自定义置信度计算：结合字段完整性和情感分析置信度"""
        base_confidence = super().calculate_confidence()
        # 将情感分析的置信度也考虑进去
        combined_confidence = (base_confidence + self.confidence_score) / 2
        return combined_confidence
