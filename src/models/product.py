"""产品信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class ProductInfo(BaseExtractionModel):
    """产品信息模型"""
    
    product_name: Optional[str] = Field(default=None, description="Product name")
    price: Optional[str] = Field(default=None, description="Price including currency symbol and amount")
    description: Optional[str] = Field(default=None, description="Concise product description")
    brand: Optional[str] = Field(default=None, description="Brand name")
    category: Optional[str] = Field(default=None, description="Product category")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "product_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "产品信息（名称、价格、品牌、描述）"
