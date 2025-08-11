"""RESTful API service for OCR-based info extraction powered by LangChain."""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ocr_client import OCRClient


class Person(BaseModel):
    """Person info model."""

    full_name: Optional[str] = Field(default=None, description="Full name")
    job_title: Optional[str] = Field(default=None, description="Job title")
    company_name: Optional[str] = Field(default=None, description="Company name")
    confidence: float = Field(default=0.0, description="Extraction confidence")


class ExtractionResponse(BaseModel):
    """API response model."""

    success: bool = Field(description="Whether processing succeeded")
    data: Optional[Person] = Field(default=None, description="Extracted person info")
    error_message: Optional[str] = Field(default=None, description="Error message")
    ocr_text: Optional[str] = Field(default=None, description="Raw OCR text")


class LangChainExtractor:
    """LangChain-based extractor with structured outputs."""

    def __init__(self):
        """Initialize extractor, model and prompt template."""
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert information extractor. Extract person info from OCR text. "
                    "Input typically comes from business cards or profile screenshots and contains a full name, job title and company name. "
                    "Follow these rules strictly:"
                    "1. Full name: usually the most prominent text, often on the first line. "
                    "2. Job title: includes keywords like Director, Manager, Engineer, Analyst. "
                    "3. Company: may include suffixes like Inc, Corp, LLC, Co. "
                    "4. If a field cannot be determined, return null. "
                    "5. Extract only explicit information; do not guess.",
                ),
                ("human", "Extract person info from the following OCR text:\n\n{text}"),
            ]
        )

        # Initialize LLM from environment variables
        # Supported env vars: LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
        llm_model = os.getenv("LLM_MODEL", "qwen3:4b-instruct-2507-fp16")
        llm_base_url = os.getenv("LLM_BASE_URL","http://0.0.0.0:11434/v1")
        llm_api_key = os.getenv("LLM_API_KEY","fake_key")

        if llm_api_key:
            self.llm = ChatOpenAI(
                model=llm_model, base_url=llm_base_url, api_key=llm_api_key, temperature=0
            )
            self.structured_llm = self.llm.with_structured_output(schema=Person)
        else:
            self.llm = None
            self.structured_llm = None

        if self.llm is None:
            print(
                "Warning: No LLM API key found. /extract_text will still work with a heuristic fallback."
            )

    def extract_person_info(self, text: str) -> Person:
        """Extract person info from OCR text."""
        try:
            if not text or not text.strip():
                return Person()

            # Create prompt
            prompt = self.prompt_template.invoke({"text": text})

            if self.structured_llm is not None:
                # LLM structured extraction
                result = self.structured_llm.invoke(prompt)
            else:
                # Heuristic fallback
                lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                full_name = lines[0].lstrip("#").strip() if len(lines) >= 1 else None
                job_title = lines[1].lstrip("#").strip() if len(lines) >= 2 else None
                company_name = (
                    lines[2].lstrip("#").strip() if len(lines) >= 3 else None
                )
                result = Person(
                    full_name=full_name,
                    job_title=job_title,
                    company_name=company_name,
                )

            # Compute confidence
            confidence = self._calculate_confidence(result)
            result.confidence = confidence

            return result

        except Exception as e:
            print(f"LangChain extraction error: {e}")
            return Person(confidence=0.0)

    def _calculate_confidence(self, person: Person) -> float:
        """Compute extraction confidence as fraction of present fields."""
        filled_fields = 0
        total_fields = 3

        if person.full_name:
            filled_fields += 1
        if person.job_title:
            filled_fields += 1
        if person.company_name:
            filled_fields += 1

        return filled_fields / total_fields


def create_app() -> FastAPI:
    """FastAPI app factory."""
    app = FastAPI(
        title="LangChain OCR Extraction API",
        description="Extract full name, job title and company from screenshots using OCR and LangChain",
        version="1.0.0",
    )

    # Initialize components
    ocr_client = OCRClient()
    extractor = LangChainExtractor()

    @app.post("/extract", response_model=ExtractionResponse)
    async def extract_person_info(file: UploadFile = File(...)):
        """Extract person info from an uploaded image file."""
        # Validate content type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Please upload an image file")

        # Save to a temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as temp_file:
            try:
                # Write content
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()

                # OCR
                ocr_text = ocr_client.extract_text_from_image(temp_file.name)

                if ocr_text is None:
                    return ExtractionResponse(
                        success=False,
                        error_message=
                        "OCR text extraction failed. Ensure OCR service is running.",
                    )

                # LangChain extract
                person_info = extractor.extract_person_info(ocr_text)

                return ExtractionResponse(
                    success=True, data=person_info, ocr_text=ocr_text
                )

            except Exception as e:  # noqa: BLE001
                return ExtractionResponse(success=False, error_message=f"Processing error: {str(e)}")
            finally:
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass
    return app


# Create module-level app for ASGI discovery
app = create_app()


def main():
    """Run the API server with uvicorn."""
    logging.info("Starting LangChain OCR Extraction API...")
    logging.info("Docs: http://0.0.0.0:8001/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


if __name__ == "__main__":
    main()


