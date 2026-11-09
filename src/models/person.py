"""人员信息模型"""

from typing import Optional
from pydantic import Field
from .base import BaseExtractionModel


class Person(BaseExtractionModel):
    """人员信息模型"""
    
    full_name: Optional[str] = Field(default=None, description="Full name")
    job_title: Optional[str] = Field(default=None, description="Job title")
    company_name: Optional[str] = Field(default=None, description="Company name")
    
    @classmethod
    def get_extraction_type(cls) -> str:
        return "person"
    
    @classmethod
    def get_description(cls) -> str:
        return "人员信息（姓名、职位、公司）"
