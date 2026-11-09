"""联系信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class ContactInfo(BaseExtractionModel):
    """联系信息模型"""
    
    name: Optional[str] = Field(default=None, description="Contact name")
    phone: Optional[str] = Field(default=None, description="Phone number in its original format")
    email: Optional[str] = Field(default=None, description="Email address")
    address: Optional[str] = Field(default=None, description="Postal address")
    wechat: Optional[str] = Field(default=None, description="WeChat ID")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "contact_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "联系信息（姓名、电话、邮箱、地址）"
