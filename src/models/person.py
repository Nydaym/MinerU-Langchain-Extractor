"""人员信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class Person(BaseExtractionModel):
    """人员信息模型"""
    
    full_name: Optional[str] = Field(default=None, description="姓名")
    job_title: Optional[str] = Field(default=None, description="职位")
    company_name: Optional[str] = Field(default=None, description="公司名称")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "person"
    
    @classmethod
    def get_description(cls) -> str:
        return "人员信息（姓名、职位、公司）"
