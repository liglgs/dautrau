"""Bộ sinh vector cho RAG.

Hai nhà cung cấp:
  * ``gemini`` — gọi ``batchEmbedContents`` của Google Gemini, dùng chung vòng xoay khóa
    với tầng mô hình (``src.ai.transport.get_next_gemini_key``).
  * ``hash`` — băm đặc trưng n-gram cục bộ, chạy offline, dùng cho kiểm thử và máy không có khóa.

Vector phải tất định với cùng đầu vào; sai số cho phép được ghi trong báo cáo chất lượng.
"""

from __future__ import annotations

import hashlib
import math
import time
from typing import Protocol

import httpx

from src.ai.transport import get_gemini_keys_pool, get_next_gemini_key
from src.config import Settings, get_settings
from src.vmec import DomainError

GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
BATCH_SIZE = 16
KEY_MIN_INTERVAL_SECONDS = 1.0


class Embedder(Protocol):
    model_name: str
    dimension: int
    provider: str

    def encode(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]: ...


def _l2(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


class HashEmbedder:
    """Vector băm n-gram, tất định, không cần mạng."""

    provider = "hash"
    dimension = 384

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.model_name = f"hash-ngram-{dimension}"

    def encode(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        return [self._one(text) for text in texts]

    def _one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        normalized = " ".join((text or "").lower().split())
        tokens = normalized.split(" ")
        grams: list[str] = list(tokens)
        for n in (2, 3, 4):
            grams.extend(" ".join(tokens[i:i + n]) for i in range(max(0, len(tokens) - n + 1)))
        for gram in grams:
            if not gram:
                continue
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        return _l2(vector)


class GeminiEmbedder:
    provider = "gemini"
    dimension = 3072

    def __init__(self, model_name: str, settings: Settings | None = None):
        self.model_name = model_name
        self.settings = settings or get_settings()
        self._last_key_call: dict[str, float] = {}
        if not self.settings.gemini_keys:
            raise DomainError(503, "EMBEDDING_UNAVAILABLE", "Chưa cấu hình khóa Gemini để sinh vector.", True)

    def encode(self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            vectors.extend(self._batch(texts[start:start + BATCH_SIZE], task_type))
        return vectors

    def _pace(self, key: str) -> None:
        previous = self._last_key_call.get(key)
        if previous is not None:
            wait = KEY_MIN_INTERVAL_SECONDS - (time.monotonic() - previous)
            if wait > 0:
                time.sleep(wait)
        self._last_key_call[key] = time.monotonic()

    def _batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        url = GEMINI_EMBED_URL.format(model=self.model_name)
        pool = get_gemini_keys_pool(self.settings)
        attempts = max(6, len(pool) * 2)
        last_error = "unknown"
        for attempt in range(attempts):
            key, _ = get_next_gemini_key(self.settings)
            self._pace(key)
            payload = {
                "requests": [
                    {
                        "model": f"models/{self.model_name}",
                        "content": {"parts": [{"text": text[:8000]}]},
                        "taskType": task_type,
                    }
                    for text in texts
                ]
            }
            try:
                # Khoá gửi qua header (không nằm trong query string để tránh lọt vào log/proxy).
                with httpx.Client(timeout=60, trust_env=False) as client:
                    response = client.post(url, headers={"x-goog-api-key": key}, json=payload)
            except httpx.HTTPError as exc:  # pragma: no cover - lỗi mạng
                last_error = f"network: {exc.__class__.__name__}"
                time.sleep(0.5 * min(attempt + 1, 3))
                continue
            if response.status_code == 200:
                embeddings = response.json().get("embeddings", [])
                if len(embeddings) != len(texts):
                    raise DomainError(502, "EMBEDDING_RESPONSE_INVALID", "Số vector trả về không khớp số văn bản.")
                return [list(item["values"]) for item in embeddings]
            last_error = f"http {response.status_code}"
            if response.status_code in {401, 403}:
                # Khoá hỏng/hết quyền chỉ là lỗi của **một** khoá: đổi khoá khác rồi thử lại.
                last_error = f"http {response.status_code} (khoá bị từ chối)"
                continue
            if response.status_code in {429, 500, 502, 503, 504}:
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.replace(".", "", 1).isdigit() else 1.5 * (attempt + 1)
                time.sleep(min(delay, 15.0))
                continue
            raise DomainError(502, "EMBEDDING_REQUEST_INVALID", f"Yêu cầu sinh vector bị từ chối ({response.status_code}).")
        raise DomainError(503, "EMBEDDING_UNAVAILABLE", f"Không sinh được vector sau {attempts} lần thử ({last_error}).", True)


def get_embedder(settings: Settings | None = None) -> Embedder:
    settings = settings or get_settings()
    provider = settings.rag_embedding_provider
    if provider == "hash":
        return HashEmbedder()
    if provider == "gemini":
        return GeminiEmbedder(settings.rag_embedding_model, settings)
    if settings.gemini_keys:
        return GeminiEmbedder(settings.rag_embedding_model, settings)
    return HashEmbedder()
