"""产品信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class ProductInfo(BaseExtractionModel):
    """产品信息模型"""
    
    product_name: Optional[str] = Field(default=None, description="产品名称")
    price: Optional[str] = Field(default=None, description="价格")
    description: Optional[str] = Field(default=None, description="产品描述")
    brand: Optional[str] = Field(default=None, description="品牌")
    category: Optional[str] = Field(default=None, description="分类")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "product_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "产品信息（名称、价格、品牌、描述）"
