"""OCR client to call an existing OCR API service (MinerU)."""

import requests
from typing import Optional, Dict, Any
from pathlib import Path


class OCRClient:
    """Client for a local OCR API service (default: MinerU at 127.0.0.1:8000)."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        Initialize the OCR client.

        Args:
            base_url: Base URL of the OCR service.
        """
        self.base_url = base_url
        self.parse_endpoint = f"{base_url}/file_parse"

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
                print(f"Image file does not exist: {image_path}")
                return None

            # Prepare request
            with open(image_path, "rb") as file:
                files = {"files": file}
                headers = {"Accept": "application/json"}

                # Send request
                response = requests.post(
                    self.parse_endpoint,
                    headers=headers,
                    files=files,
                    timeout=30,
                )

                if response.status_code == 200:
                    result = response.json()
                    return self._extract_md_content(result)
                else:
                    print(
                        f"OCR API request failed. status: {response.status_code}"
                    )
                    print(f"response: {response.text}")
                    return None

        except requests.exceptions.RequestException as e:
            print(f"Error while requesting OCR API: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error while processing image: {e}")
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
                print("No 'results' field in OCR API response")
                return None

            # Return the first 'md_content' found
            for _, value in results.items():
                if isinstance(value, dict) and "md_content" in value:
                    return value["md_content"]

            print("No 'md_content' field found in OCR API response")
            return None

        except Exception as e:
            print(f"Error parsing OCR API response: {e}")
            return None


