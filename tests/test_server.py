import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.models.person import Person
from src.ocr_client import OCRClient
from src.server import create_app
from src.extractors.langchain_extractor import ExtractionError


class ServerTests(unittest.TestCase):
    def make_client(self, ocr_client):
        with patch("src.server.OCRClient", return_value=ocr_client):
            app = create_app()
        return TestClient(app)

    def test_extract_accepts_pdf_and_image(self):
        ocr = MagicMock()
        ocr.extract_text_from_image.return_value = "# Ada Lovelace"
        client = self.make_client(ocr)
        registry_extract = patch(
            "src.server.registry.extract",
            return_value=[Person(full_name="Ada Lovelace")],
        )
        with registry_extract as extract:
            for filename, content_type, content in (
                ("profile.pdf", "application/pdf", b"%PDF-example"),
                ("profile.png", "image/png", b"\x89PNG\r\n"),
            ):
                with self.subTest(filename=filename):
                    response = client.post(
                        "/extract",
                        files={"file": (filename, content, content_type)},
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.json()["success"])
                    self.assertEqual(response.json()["ocr_text"], "# Ada Lovelace")
            self.assertEqual(ocr.extract_text_from_image.call_count, 2)
            self.assertEqual(extract.call_count, 2)

    def test_legacy_extract_person_endpoint_uses_registry(self):
        ocr = MagicMock()
        ocr.extract_text_from_image.return_value = "# Ada Lovelace"
        client = self.make_client(ocr)
        with patch(
            "src.server.registry.extract",
            return_value=[Person(full_name="Ada Lovelace")],
        ) as extract:
            response = client.post(
                "/extract_person",
                files={"file": ("profile.jpg", b"\xff\xd8\xff", "image/jpeg")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["extraction_type"], "person")
        extract.assert_called_once_with("# Ada Lovelace", "person")

    def test_missing_mineru_token_returns_safe_api_error(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "mineru", "MINERU_API_TOKEN": ""}):
            client = self.make_client(OCRClient())
            response = client.post(
                "/extract",
                files={"file": ("profile.pdf", b"%PDF-example", "application/pdf")},
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertIn("MINERU_API_TOKEN", body["error_message"])
        self.assertNotIn("Bearer", body["error_message"])
        self.assertIsNone(body["ocr_text"])

    def test_rejects_invalid_and_empty_uploads(self):
        ocr = MagicMock()
        client = self.make_client(ocr)
        invalid = client.post(
            "/extract",
            files={"file": ("profile.txt", b"not an image", "text/plain")},
        )
        empty = client.post(
            "/extract",
            files={"file": ("empty.pdf", b"", "application/pdf")},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(empty.status_code, 400)
        ocr.extract_text_from_image.assert_not_called()

    def test_extraction_validation_failure_is_not_reported_as_success(self):
        ocr = MagicMock()
        ocr.extract_text_from_image.return_value = "private OCR text"
        client = self.make_client(ocr)
        with patch("src.server.registry.extract", side_effect=ExtractionError("DeepSeek 输出校验失败")):
            response = client.post("/extract", files={"file": ("sample.pdf", b"%PDF-example", "application/pdf")})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error_message"], "DeepSeek 输出校验失败")
        self.assertIsNone(response.json()["data"])


if __name__ == "__main__":
    unittest.main()
