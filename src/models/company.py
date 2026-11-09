"""公司信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class CompanyInfo(BaseExtractionModel):
    """公司信息模型"""
    
    company_name: Optional[str] = Field(default=None, description="Company name")
    industry: Optional[str] = Field(default=None, description="Industry")
    address: Optional[str] = Field(default=None, description="Postal address")
    phone: Optional[str] = Field(default=None, description="Phone number in its original format")
    email: Optional[str] = Field(default=None, description="Email address")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "company_info"
    
    @classmethod
    def get_description(cls) -> str:
        return "公司信息（名称、行业、联系方式）"
