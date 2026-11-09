import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from src.mineru_client import MinerUClient, MinerUError
from src.ocr_client import OCRClient, LocalOCRClient


def response(data=None, status=200):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status_code = status
    result.json.return_value = data
    return result


class MinerUTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "MINERU_API_TOKEN": "test-token", "MINERU_MODEL_VERSION": "vlm",
            "MINERU_POLL_INTERVAL_SECONDS": "0.001", "MINERU_TASK_TIMEOUT_SECONDS": "5",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "sample.pdf"
        self.path.write_bytes(b"%PDF-example")
        self.client = MinerUClient()
        self.api, self.storage = MagicMock(), MagicMock()
        self.api.__enter__.return_value = self.api
        self.storage.__enter__.return_value = self.storage
        self.sessions = patch("src.mineru_client.requests.Session", side_effect=[self.api, self.storage])
        self.sessions.start()
        self.addCleanup(self.sessions.stop)
        self.states = ["pending", "done"]
        self.api.request.side_effect = self.api_request
        self.storage.put.return_value = response()
        self.archive("full.md", "# 示例内容")

    def archive(self, name, text):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as result:
            result.writestr(name, text)
        download = response()
        download.iter_content.return_value = [data.getvalue()]
        self.storage.get.return_value = download

    def api_request(self, method, url, **kwargs):
        if method == "POST":
            self.data_id = kwargs["json"]["files"][0]["data_id"]
            self.assertEqual(kwargs["json"]["model_version"], "vlm")
            return response({"code": 0, "data": {"batch_id": "batch", "file_urls": ["https://storage.example/upload"]}})
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return response({"code": 0, "data": {"extract_result": [{
            "data_id": self.data_id, "state": state,
            "full_zip_url": "https://storage.example/result.zip",
        }]}})

    def test_upload_poll_download_without_leaking_bearer_to_storage(self):
        self.assertEqual(self.client.extract_text_from_image(str(self.path)), "# 示例内容")
        self.assertEqual(self.api.request.call_count, 3)
        self.assertEqual(self.api.request.call_args.kwargs["headers"], {"Authorization": "Bearer test-token"})
        self.assertNotIn("headers", self.storage.put.call_args.kwargs)
        self.assertNotIn("headers", self.storage.get.call_args.kwargs)
        self.assertFalse(self.storage.put.call_args.kwargs["allow_redirects"])

    def test_missing_token_fails_before_network(self):
        self.client.token = ""
        with self.assertRaisesRegex(MinerUError, "MINERU_API_TOKEN"):
            self.client.extract_text_from_image(str(self.path))
        self.api.request.assert_not_called()

    def test_auth_failure_is_safe(self):
        self.api.request.side_effect = None
        self.api.request.return_value = response(status=401)
        with self.assertRaisesRegex(MinerUError, "Token 无效"):
            self.client.extract_text_from_image(str(self.path))

    def test_failed_task(self):
        self.states = ["failed"]
        with self.assertRaisesRegex(MinerUError, "解析失败"):
            self.client.extract_text_from_image(str(self.path))

    def test_poll_deadline(self):
        self.states = ["running"]
        self.client.task_timeout = 0.01
        with self.assertRaisesRegex(MinerUError, "超时"):
            self.client.extract_text_from_image(str(self.path))

    def test_missing_or_oversized_markdown(self):
        self.archive("other.txt", "not markdown")
        with self.assertRaisesRegex(MinerUError, "full.md"):
            self.client.extract_text_from_image(str(self.path))

    def test_archive_size_bound(self):
        self.client.MAX_ARCHIVE_BYTES = 1
        with self.assertRaisesRegex(MinerUError, "压缩包超过"):
            self.client.extract_text_from_image(str(self.path))

    def test_request_exception_does_not_expose_signed_url(self):
        self.api.request.side_effect = requests.ConnectionError("https://example.com/?secret=test-token")
        with self.assertRaises(MinerUError) as caught:
            self.client.extract_text_from_image(str(self.path))
        self.assertNotIn("test-token", str(caught.exception))

    def test_backend_selection(self):
        with patch.dict(os.environ, {"OCR_BACKEND": "local"}):
            self.assertIsInstance(OCRClient().client, LocalOCRClient)
        with patch.dict(os.environ, {"OCR_BACKEND": "mineru"}):
            self.assertIsInstance(OCRClient().client, MinerUClient)


if __name__ == "__main__":
    unittest.main()
