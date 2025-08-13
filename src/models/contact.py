"""联系信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class ContactInfo(BaseExtractionModel):
    """联系信息模型"""
    
    name: Optional[str] = Field(default=None, description="姓名")
    phone: Optional[str] = Field(default=None, description="电话")
    email: Optional[str] = Field(default=None, description="邮箱")
    address: Optional[str] = Field(default=None, description="地址")
    wechat: Optional[str] = Field(default=None, description="微信")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "contact_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "联系信息（姓名、电话、邮箱、地址）"
