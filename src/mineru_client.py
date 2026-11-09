"""MinerU hosted v4 API: upload, poll, and read full.md without extracting files."""

import io
import math
import os
import time
import uuid
import zipfile
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests


class MinerUError(ValueError):
    """A safe, user-facing error without credentials or signed URLs."""


class MinerUClient:
    API_URL = "https://mineru.net/api/v4"
    MAX_FILE_BYTES = 200 * 1024 * 1024
    MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
    MAX_MARKDOWN_BYTES = 16 * 1024 * 1024

    def __init__(self):
        self.token = os.getenv("MINERU_API_TOKEN", "").strip()
        self.model_version = os.getenv("MINERU_MODEL_VERSION", "vlm")
        if self.model_version not in {"vlm", "pipeline"}:
            raise MinerUError("MINERU_MODEL_VERSION 必须是 vlm 或 pipeline")
        self.timeout = self._seconds("OCR_TIMEOUT_SECONDS", "30")
        self.task_timeout = self._seconds("MINERU_TASK_TIMEOUT_SECONDS", "300")
        self.poll_interval = self._seconds("MINERU_POLL_INTERVAL_SECONDS", "2")

    @staticmethod
    def _seconds(name, default):
        try:
            value = float(os.getenv(name, default))
            if not math.isfinite(value) or value <= 0:
                raise ValueError
            return value
        except ValueError:
            raise MinerUError(f"{name} 必须是正数") from None

    def _remaining(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise MinerUError("MinerU 解析等待超时，请稍后重试")
        return min(self.timeout, remaining)

    def _api(self, session, method, path, deadline, **kwargs):
        with session.request(
            method,
            self.API_URL + path,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=self._remaining(deadline),
            allow_redirects=False,
            **kwargs,
        ) as response:
            if response.status_code in {401, 403}:
                raise MinerUError("MinerU Token 无效、已过期或没有访问权限")
            if response.status_code == 429:
                raise MinerUError("MinerU 请求限流，请稍后重试")
            if response.status_code != 200:
                raise MinerUError("MinerU API 请求失败")
            result = response.json()
        if not isinstance(result, dict) or result.get("code") != 0:
            raise MinerUError("MinerU API 拒绝请求，请检查 Token、额度和文件要求")
        data = result.get("data")
        if not isinstance(data, dict):
            raise MinerUError("MinerU API 返回的数据格式不正确")
        return data

    @staticmethod
    def _storage_url(value):
        if not isinstance(value, str):
            raise MinerUError("MinerU 未返回有效的文件链接")
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise MinerUError("MinerU 未返回有效的 HTTPS 文件链接")
        return value

    def extract_text_from_image(self, image_path):
        """Keep the existing client interface; PDF files are also accepted."""
        if not self.token:
            raise MinerUError("请配置 MINERU_API_TOKEN 以使用 MinerU 在线服务")
        path = Path(image_path)
        if not path.is_file() or not 0 < path.stat().st_size <= self.MAX_FILE_BYTES:
            raise MinerUError("文件必须存在、非空且不超过 200 MiB")
        deadline = time.monotonic() + self.task_timeout
        data_id = uuid.uuid4().hex
        try:
            # Per-call sessions avoid shared mutable state across worker threads.
            with requests.Session() as api, requests.Session() as storage:
                data = self._api(api, "POST", "/file-urls/batch", deadline, json={
                    "files": [{"name": path.name, "data_id": data_id}],
                    "model_version": self.model_version,
                })
                batch_id = data.get("batch_id")
                urls = data.get("file_urls")
                if not isinstance(batch_id, str) or not batch_id or not isinstance(urls, list) or len(urls) != 1:
                    raise MinerUError("MinerU 未返回有效的上传任务")
                upload_url = self._storage_url(urls[0])
                # Do not attach the API bearer token or Content-Type to signed PUTs.
                with path.open("rb") as source, storage.put(
                    upload_url, data=source, timeout=self._remaining(deadline),
                    allow_redirects=False,
                ) as response:
                    if response.status_code not in {200, 201, 204}:
                        raise MinerUError("上传文件到 MinerU 失败")
                while True:
                    data = self._api(
                        api, "GET", f"/extract-results/batch/{quote(batch_id, safe='')}", deadline
                    )
                    results = data.get("extract_result", [])
                    if not isinstance(results, list):
                        raise MinerUError("MinerU 任务结果格式不正确")
                    item = next((r for r in results if isinstance(r, dict) and r.get("data_id") == data_id), None)
                    if item:
                        state = item.get("state")
                        if state == "done":
                            return self._download_markdown(storage, item.get("full_zip_url"), deadline)
                        if state == "failed":
                            raise MinerUError("MinerU 文件解析失败，请在官方任务记录中检查原因")
                        if state not in {"waiting-file", "pending", "running", "converting"}:
                            raise MinerUError("MinerU 返回了未知的任务状态")
                    time.sleep(min(self.poll_interval, self._remaining(deadline)))
        except MinerUError:
            raise
        except (requests.RequestException, OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError):
            # Upstream exceptions can contain signed URLs or sensitive response bodies.
            raise MinerUError("MinerU 在线解析失败：网络异常或结果格式无效") from None

    def _download_markdown(self, session, url, deadline):
        archive = io.BytesIO()
        with session.get(
            self._storage_url(url), stream=True, timeout=self._remaining(deadline),
            allow_redirects=False,
        ) as response:
            if response.status_code != 200:
                raise MinerUError("下载 MinerU 解析结果失败")
            for chunk in response.iter_content(chunk_size=64 * 1024):
                self._remaining(deadline)
                if archive.tell() + len(chunk) > self.MAX_ARCHIVE_BYTES:
                    raise MinerUError("MinerU 结果压缩包超过本服务 64 MiB 限制")
                archive.write(chunk)
        archive.seek(0)
        with zipfile.ZipFile(archive) as result:
            candidates = [i for i in result.infolist() if not i.is_dir() and Path(i.filename).name == "full.md"]
            if len(candidates) != 1:
                raise MinerUError("MinerU 结果中未找到唯一的 full.md")
            entry = candidates[0]
            if entry.file_size > self.MAX_MARKDOWN_BYTES:
                raise MinerUError("MinerU Markdown 超过本服务 16 MiB 限制")
            with result.open(entry) as source:
                content = source.read(self.MAX_MARKDOWN_BYTES + 1)
            if len(content) > self.MAX_MARKDOWN_BYTES:
                raise MinerUError("MinerU Markdown 超过本服务 16 MiB 限制")
        text = content.decode("utf-8-sig")
        if not text.strip():
            raise MinerUError("MinerU 返回了空的 Markdown")
        return text
