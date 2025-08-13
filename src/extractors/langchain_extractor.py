"""LangChain抽取器实现"""

import os
import re
from typing import List, Dict, Any, Type
from pydantic import create_model, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .base import BaseExtractor
from ..models.base import BaseExtractionModel
from ..models import Person, Sentiment, CompanyInfo, ProductInfo, ContactInfo


class LangChainExtractor(BaseExtractor):
    """基于LangChain的通用信息抽取器"""
    
    def __init__(self):
        """初始化抽取器"""
        
        # 不同抽取类型的系统提示模板
        self.system_prompts = {
            "person": (
                "你是一个专业的人员信息抽取专家。从OCR文本中抽取人员信息。"
                "输入通常来自名片、个人资料截图或合影等，可能包含一个或多个人员。"
                "严格遵循以下规则："
                "1. 抽取文本中发现的所有人员，即使有多个人。"
                "2. 姓名：通常是最突出的文本，经常在第一行。"
                "3. 职位：包括如主管、经理、工程师、分析师等关键词。"
                "4. 公司：可能包含Inc、Corp、LLC、Co等后缀。"
                "5. 如果某个字段无法确定，返回null。"
                "6. 只抽取明确的信息，不要猜测。"
                "7. 返回所找到的所有人员列表，即使只有一个人。"
            ),
            "sentiment": (
                "你是一个专业的情感分析专家。从OCR文本中分析情感倾向。"
                "严格遵循以下规则："
                "1. 分析文本的整体情感倾向：positive（积极）、negative（消极）或neutral（中性）。"
                "2. 给出0-1之间的置信度分数，表示情感分析的可靠性。"
                "3. 提取影响情感判断的关键词。"
                "4. 如果文本过于简短或模糊，适当降低置信度。"
                "5. 只分析明确的情感表达，不要过度解读。"
            ),
            "company_info": (
                "你是一个专业的公司信息抽取专家。从OCR文本中抽取公司相关信息。"
                "严格遵循以下规则："
                "1. 抽取公司名称、行业、地址、电话、邮箱等信息。"
                "2. 公司名称可能包含Inc、Corp、LLC、Co、Ltd等后缀。"
                "3. 地址信息要完整，包括街道、城市、邮编等。"
                "4. 电话格式可能多样，保持原格式。"
                "5. 如果某个字段无法确定，返回null。"
                "6. 只抽取明确的信息，不要猜测。"
            ),
            "product_info": (
                "你是一个专业的产品信息抽取专家。从OCR文本中抽取产品相关信息。"
                "严格遵循以下规则："
                "1. 抽取产品名称、价格、描述、品牌、分类等信息。"
                "2. 价格信息包括货币符号和数值。"
                "3. 产品描述要简洁明了。"
                "4. 品牌名称通常比较醒目。"
                "5. 分类可能包括产品类型、用途等。"
                "6. 如果某个字段无法确定，返回null。"
                "7. 只抽取明确的信息，不要猜测。"
            ),
            "contact_info": (
                "你是一个专业的联系信息抽取专家。从OCR文本中抽取联系方式。"
                "严格遵循以下规则："
                "1. 抽取姓名、电话、邮箱、地址、微信等联系信息。"
                "2. 电话号码格式可能多样，保持原格式。"
                "3. 邮箱地址必须包含@符号。"
                "4. 地址信息要尽可能完整。"
                "5. 微信号通常以英文字母开头。"
                "6. 如果某个字段无法确定，返回null。"
                "7. 只抽取明确的信息，不要猜测。"
            )
        }
        
        # 初始化LLM
        self._init_llm()
    
    def _init_llm(self):
        """初始化LLM"""
        llm_model = os.getenv("LLM_MODEL", "qwen3:4b-instruct-2507-fp16")
        llm_base_url = os.getenv("LLM_BASE_URL", "http://0.0.0.0:11434/v1")
        llm_api_key = os.getenv("LLM_API_KEY", "fake_key")

        if llm_api_key:
            self.llm = ChatOpenAI(
                model=llm_model, base_url=llm_base_url, api_key=llm_api_key, temperature=0
            )
        else:
            self.llm = None

        if self.llm is None:
            print("警告：未找到LLM API密钥。将使用启发式回退方法工作。")
    
    def extract(
        self, 
        text: str, 
        model_class: Type[BaseExtractionModel]
    ) -> List[BaseExtractionModel]:
        """抽取信息"""
        try:
            if not text or not text.strip():
                return []

            extraction_type = model_class.get_extraction_type()
            
            # 创建列表模型
            list_model_name = f"{model_class.__name__}List"
            list_model = create_model(
                list_model_name,
                items=(List[model_class], Field(description=f"抽取的{model_class.__name__}列表"))
            )

            # 创建提示模板
            system_prompt = self.system_prompts.get(extraction_type, "")
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "从以下OCR文本中抽取信息：\n\n{text}")
            ])

            if self.llm is not None:
                # 使用LLM进行结构化抽取
                structured_llm = self.llm.with_structured_output(schema=list_model)
                prompt = prompt_template.invoke({"text": text})
                result = structured_llm.invoke(prompt)
                items = getattr(result, 'items', [])
            else:
                # 启发式回退方法
                items = self._heuristic_extraction(text, extraction_type, model_class)

            # 更新置信度
            for item in items:
                item.update_confidence()

            return items

        except Exception as e:
            print(f"信息抽取错误: {e}")
            return []
    
    def supports_model(self, model_class: Type[BaseExtractionModel]) -> bool:
        """检查是否支持指定的模型类型"""
        extraction_type = model_class.get_extraction_type()
        return extraction_type in self.system_prompts
    
    def _heuristic_extraction(
        self, 
        text: str, 
        extraction_type: str, 
        model_class: Type[BaseExtractionModel]
    ) -> List[BaseExtractionModel]:
        """启发式抽取回退方法"""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        
        if extraction_type == "person":
            return self._heuristic_person_extraction(lines, model_class)
        elif extraction_type == "sentiment":
            return self._heuristic_sentiment_extraction(text, model_class)
        elif extraction_type == "company_info":
            return self._heuristic_company_extraction(lines, model_class)
        elif extraction_type == "product_info":
            return self._heuristic_product_extraction(lines, model_class)
        elif extraction_type == "contact_info":
            return self._heuristic_contact_extraction(lines, model_class)
        else:
            return []

    def _heuristic_person_extraction(self, lines: List[str], model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        """人员信息启发式抽取"""
        if not lines:
            return []
        
        full_name = lines[0].lstrip("#").strip() if len(lines) >= 1 else None
        job_title = lines[1].lstrip("#").strip() if len(lines) >= 2 else None
        company_name = lines[2].lstrip("#").strip() if len(lines) >= 3 else None
        
        person = model_class(
            full_name=full_name,
            job_title=job_title,
            company_name=company_name
        )
        return [person]

    def _heuristic_sentiment_extraction(self, text: str, model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        """情感分析启发式抽取"""
        positive_words = ["好", "棒", "优秀", "满意", "喜欢", "推荐", "excellent", "good", "great", "awesome"]
        negative_words = ["差", "坏", "糟糕", "失望", "不满", "讨厌", "bad", "terrible", "awful", "poor"]
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            confidence_score = min(0.8, positive_count * 0.2)
        elif negative_count > positive_count:
            sentiment = "negative"
            confidence_score = min(0.8, negative_count * 0.2)
        else:
            sentiment = "neutral"
            confidence_score = 0.5
        
        keywords = [word for word in positive_words + negative_words if word in text_lower]
        
        sentiment_obj = model_class(
            sentiment=sentiment,
            confidence_score=confidence_score,
            keywords=keywords[:5]
        )
        return [sentiment_obj]

    def _heuristic_company_extraction(self, lines: List[str], model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        """公司信息启发式抽取"""
        company_info = model_class()
        
        for line in lines:
            if any(suffix in line.lower() for suffix in ['inc', 'corp', 'llc', 'co', 'ltd', '公司', '有限']):
                company_info.company_name = line
            elif any(keyword in line.lower() for keyword in ['tel', '电话', 'phone']):
                phone_pattern = r'[\d\-\(\)\+\s]+'
                phone_match = re.search(phone_pattern, line)
                if phone_match:
                    company_info.phone = phone_match.group().strip()
            elif '@' in line:
                company_info.email = line
        
        return [company_info]

    def _heuristic_product_extraction(self, lines: List[str], model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        """产品信息启发式抽取"""
        product_info = model_class()
        
        for line in lines:
            if any(symbol in line for symbol in ['¥', '$', '￥', '元', 'USD', 'CNY']):
                product_info.price = line
            elif not product_info.product_name and len(line) > 2:
                product_info.product_name = line
        
        return [product_info]

    def _heuristic_contact_extraction(self, lines: List[str], model_class: Type[BaseExtractionModel]) -> List[BaseExtractionModel]:
        """联系信息启发式抽取"""
        contact_info = model_class()
        
        for line in lines:
            if '@' in line:
                contact_info.email = line
            elif any(keyword in line.lower() for keyword in ['tel', '电话', 'phone']):
                phone_pattern = r'[\d\-\(\)\+\s]+'
                phone_match = re.search(phone_pattern, line)
                if phone_match:
                    contact_info.phone = phone_match.group().strip()
            elif not contact_info.name and len(line) > 1:
                contact_info.name = line
        
        return [contact_info]
