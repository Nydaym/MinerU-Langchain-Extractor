"""OCR client to call an existing OCR API service (MinerU)."""

import logging
import os
import requests
from typing import Optional, Dict, Any
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class LocalOCRClient:
    """Client for a local OCR API service (default: MinerU at 127.0.0.1:8000)."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize the OCR client.

        Args:
            base_url: Base URL of the OCR service.
        """
        self.base_url = (base_url or os.getenv("OCR_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout = timeout or int(os.getenv("OCR_TIMEOUT_SECONDS", "30"))
        self.parse_endpoint = f"{self.base_url}/file_parse"
        self.session = requests.Session()

        retries = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["POST"]),
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def extract_text_from_image(self, image_path: str) -> Optional[str]:
        """
        Extract text from an image file.

        Args:
            image_path: Path to the image file.

        Returns:
            Extracted text content, or None on failure.
        """
        try:
            # Check file exists
            if not Path(image_path).exists():
                logger.warning("Image file does not exist: %s", image_path)
                return None

            # Prepare request
            with open(image_path, "rb") as file:
                files = {"files": file}
                headers = {"Accept": "application/json"}

                # Send request
                response = self.session.post(
                    self.parse_endpoint,
                    headers=headers,
                    files=files,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    result = response.json()
                    return self._extract_md_content(result)
                else:
                    logger.error(
                        "OCR API request failed. status=%s",
                        response.status_code,
                    )
                    return None

        except requests.exceptions.RequestException as e:
            logger.error("Error while requesting local OCR API (%s)", type(e).__name__)
            return None
        except Exception as e:
            logger.error("Unexpected local OCR error (%s)", type(e).__name__)
            return None

    def _extract_md_content(self, api_response: Dict[str, Any]) -> Optional[str]:
        """
        Extract md_content from OCR API JSON response.

        Args:
            api_response: OCR API JSON response

        Returns:
            Extracted markdown content if available; otherwise None.
        """
        try:
            results = api_response.get("results", {})
            if not results:
                logger.warning("No 'results' field in OCR API response")
                return None

            # Return the first 'md_content' found
            for _, value in results.items():
                if isinstance(value, dict) and "md_content" in value:
                    return value["md_content"]

            logger.warning("No 'md_content' field found in OCR API response")
            return None

        except Exception as e:
            logger.error("Invalid local OCR response (%s)", type(e).__name__)
            return None


class OCRClient:
    """Hosted MinerU by default; explicit local settings preserve the legacy client."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        from .mineru_client import MinerUClient

        backend = os.getenv("OCR_BACKEND", "mineru").lower()
        if base_url is not None or backend == "local":
            self.client = LocalOCRClient(base_url=base_url, timeout=timeout)
        elif backend == "mineru":
            self.client = MinerUClient()
        else:
            raise ValueError("OCR_BACKEND 必须是 mineru 或 local")

    def extract_text_from_image(self, image_path: str) -> Optional[str]:
        return self.client.extract_text_from_image(image_path)

