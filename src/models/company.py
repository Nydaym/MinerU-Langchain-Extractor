"""公司信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class CompanyInfo(BaseExtractionModel):
    """公司信息模型"""
    
    company_name: Optional[str] = Field(default=None, description="公司名称")
    industry: Optional[str] = Field(default=None, description="行业")
    address: Optional[str] = Field(default=None, description="地址")
    phone: Optional[str] = Field(default=None, description="电话")
    email: Optional[str] = Field(default=None, description="邮箱")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "company_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "公司信息（名称、行业、联系方式）"
