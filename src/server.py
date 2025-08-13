"""RESTful API service for OCR-based info extraction powered by LangChain."""

import os
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse

from .models.base import ExtractionResponse
from .extractors.registry import registry
from .config.setup import setup_default_extractors
from .ocr_client import OCRClient





def create_app() -> FastAPI:
    """FastAPI应用工厂函数"""
    
    # 初始化默认抽取器和模型
    setup_default_extractors()
    
    app = FastAPI(
        title="通用OCR信息抽取API",
        description="使用OCR和LangChain从图片中抽取各种类型的信息",
        version="2.0.0",
    )

    # 初始化OCR客户端
    ocr_client = OCRClient()

    @app.get("/extraction_types")
    async def get_extraction_types():
        """获取支持的抽取类型列表"""
        return {
            "supported_types": registry.get_supported_types()
        }

    @app.post("/extract", response_model=ExtractionResponse)
    async def extract_info(
        file: UploadFile = File(...),
        extraction_type: str = Query(
            default="person",
            description="抽取类型"
        )
    ):
        """从上传的图片文件中抽取指定类型的信息"""
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="请上传图片文件")

        # 检查抽取类型是否支持
        if not registry.get_model_class(extraction_type):
            supported_types = [t["type"] for t in registry.get_supported_types()]
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的抽取类型: {extraction_type}。支持的类型: {', '.join(supported_types)}"
            )

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            try:
                # 写入文件内容
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()

                # OCR文本抽取
                ocr_text = ocr_client.extract_text_from_image(temp_file.name)

                if ocr_text is None:
                    return ExtractionResponse(
                        success=False,
                        error_message="OCR文本抽取失败，请确保OCR服务正在运行。",
                        extraction_type=extraction_type
                    )

                # 使用注册系统进行信息抽取
                extracted_items = registry.extract(ocr_text, extraction_type)
                
                # 转换为字典格式
                extracted_data = [item.model_dump() for item in extracted_items]

                return ExtractionResponse(
                    success=True,
                    data=extracted_data,
                    extraction_type=extraction_type,
                    ocr_text=ocr_text
                )

            except ValueError as e:
                return ExtractionResponse(
                    success=False,
                    error_message=str(e),
                    extraction_type=extraction_type
                )
            except Exception as e:
                return ExtractionResponse(
                    success=False,
                    error_message=f"处理错误: {str(e)}",
                    extraction_type=extraction_type
                )
            finally:
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    # 保持向后兼容性的旧接口
    @app.post("/extract_person", response_model=ExtractionResponse)
    async def extract_person_info_legacy(file: UploadFile = File(...)):
        """提取人员信息（向后兼容接口）"""
        return await extract_info(file, "person")

    return app


# Create module-level app for ASGI discovery
app = create_app()


def main():
    """使用uvicorn运行API服务器"""
    logging.info("启动通用OCR信息抽取API...")
    logging.info("API文档: http://0.0.0.0:8001/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()


