"""RESTful API service for OCR-based info extraction powered by LangChain."""

import os
import logging
import tempfile
from pathlib import Path

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from .models.base import ExtractionResponse
from .extractors.registry import registry
from .config.setup import setup_default_extractors
from .ocr_client import OCRClient

logger = logging.getLogger(__name__)




def create_app() -> FastAPI:
    """FastAPI应用工厂函数"""
    
    # 初始化默认抽取器和模型
    setup_default_extractors()
    
    app = FastAPI(
        title="通用OCR信息抽取API",
        description="使用 MinerU 在线解析和 LangChain 从图片或 PDF 中抽取信息",
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
        """从上传的图片或 PDF 文件中抽取指定类型的信息"""
        # 验证文件类型
        suffix = Path(file.filename or "").suffix.lower()
        allowed_suffixes = {".pdf", ".png", ".jpg", ".jpeg", ".jp2", ".webp", ".gif", ".bmp"}
        if suffix not in allowed_suffixes or not file.content_type or not (
            file.content_type.startswith("image/") or file.content_type == "application/pdf"
        ):
            await file.close()
            raise HTTPException(status_code=400, detail="请上传 PDF 或 PNG/JPG/JPEG/JP2/WebP/GIF/BMP 图片")

        # 检查抽取类型是否支持
        if not registry.get_model_class(extraction_type):
            supported_types = [t["type"] for t in registry.get_supported_types()]
            await file.close()
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的抽取类型: {extraction_type}。支持的类型: {', '.join(supported_types)}"
            )

        # 保存到临时文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / f"upload{suffix}"
            try:
                # 分块写入，避免大文件一次性读入内存
                size = 0
                with temp_path.open("wb") as temp_file:
                    while True:
                        chunk = await file.read(1024 * 1024)
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > 200 * 1024 * 1024:
                            raise HTTPException(status_code=413, detail="文件不能超过 200 MiB")
                        temp_file.write(chunk)
                if not size:
                    raise HTTPException(status_code=400, detail="文件不能为空")

                # OCR文本抽取（在线程池执行，避免阻塞事件循环）
                ocr_text = await run_in_threadpool(
                    ocr_client.extract_text_from_image,
                    str(temp_path),
                )

                if ocr_text is None:
                    return ExtractionResponse(
                        success=False,
                        error_message="OCR 文本抽取失败，请检查所选 OCR 服务的配置。",
                        extraction_type=extraction_type
                    )

                # 使用注册系统进行信息抽取
                extracted_items = await run_in_threadpool(
                    registry.extract,
                    ocr_text,
                    extraction_type,
                )
                
                # 转换为字典格式
                extracted_data = [item.model_dump() for item in extracted_items]

                return ExtractionResponse(
                    success=True,
                    data=extracted_data,
                    extraction_type=extraction_type,
                    ocr_text=ocr_text
                )

            except HTTPException:
                raise
            except ValueError as e:
                logger.warning("Invalid extraction request: %s", e)
                return ExtractionResponse(
                    success=False,
                    error_message=str(e),
                    extraction_type=extraction_type
                )
            except Exception as e:
                logger.exception("Unhandled error while processing extraction request: %s", e)
                return ExtractionResponse(
                    success=False,
                    error_message=f"处理错误: {str(e)}",
                    extraction_type=extraction_type
                )
            finally:
                await file.close()

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
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.info("启动通用OCR信息抽取API...")
    logging.info("API文档: http://0.0.0.0:8001/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()

