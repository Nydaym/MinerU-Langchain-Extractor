"""系统设置和默认配置"""

from ..models import Person, Sentiment, CompanyInfo, ProductInfo, ContactInfo
from ..extractors import LangChainExtractor
from ..extractors.registry import registry


def setup_default_extractors():
    """设置默认的抽取器和模型
    
    这个函数会注册所有内置的模型类型和抽取器。
    用户可以通过类似的方式注册自定义的模型和抽取器。
    """
    
    # 注册内置模型类型
    registry.register_model(Person)
    registry.register_model(Sentiment)
    registry.register_model(CompanyInfo)
    registry.register_model(ProductInfo)
    registry.register_model(ContactInfo)
    
    # 注册默认抽取器
    langchain_extractor = LangChainExtractor()
    registry.register_extractor(langchain_extractor)
    
    print("默认抽取器和模型已设置完成")
