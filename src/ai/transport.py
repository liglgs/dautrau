"""JSON model transport for custom Chat Completions, OpenAI, and native Gemini."""

import json
import re
import threading
import time
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

import httpx

from src.config import Settings, get_settings
from src.vmec import DomainError


@dataclass(frozen=True)
class ModelResult:
    data: dict
    provider: str
    requested_model: str
    returned_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


def selected_provider(settings: Settings) -> str:
    if settings.model_provider != "auto":
        return settings.model_provider
    if settings.gemini_base_url and settings.gemini_api_key:
        return "openai_compatible"
    if settings.openai_api_key and not settings.openai_api_key.startswith("sk-your-"):
        return "openai"
    if settings.gemini_api_key:
        return "gemini"
    return "openai"

_gemini_key_index = 0
_gemini_key_lock = threading.Lock()


def get_gemini_keys_pool(settings: Settings) -> list[str]:
    keys = getattr(settings, "gemini_keys", None)
    if keys:
        return list(keys)
    if settings.gemini_api_key:
        return [settings.gemini_api_key]
    return []


def get_next_gemini_key(settings: Settings) -> tuple[str, list[str]]:
    """Lấy key hiện tại theo round-robin và trả về toàn bộ pool để hỗ trợ failover."""
    global _gemini_key_index
    pool = get_gemini_keys_pool(settings)
    if not pool:
        return "", []
    with _gemini_key_lock:
        idx = _gemini_key_index % len(pool)
        _gemini_key_index = (_gemini_key_index + 1) % len(pool)
    ordered = [pool[(idx + i) % len(pool)] for i in range(len(pool))]
    return ordered[0], ordered


def selected_model(settings: Settings, provider: str) -> str:
    defaults = {"openai": "gpt-4o-mini", "openai_compatible": "gemini-3.6-flash-high", "gemini": "gemini-3.5-flash-lite"}
    return settings.model_name or defaults[provider]


def chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.query or parsed.fragment:
        raise DomainError(422, "MODEL_CONFIG_INVALID", "Base URL mô hình không hợp lệ.")
    if not parsed.path or parsed.path == "/":
        base += "/v1"
    return base + "/chat/completions"


def _response_error(exc: httpx.HTTPError) -> tuple[int, str, bool]:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return 403, "MODEL_PERMISSION_DENIED", False
        if status in (400, 404, 422):
            return 422, "MODEL_REQUEST_INVALID", False
        return 503, "MODEL_UNAVAILABLE", status in (429, 500, 502, 503, 504)
    return 503, "MODEL_UNAVAILABLE", True


def complete_json(system: str, user: str, settings: Settings | None = None) -> ModelResult:
    settings = settings or get_settings()
    provider = selected_provider(settings)
    model = selected_model(settings, provider)
    if provider == "gemini":
        primary_key, key_pool = get_next_gemini_key(settings)
        if not primary_key or primary_key.startswith("sk-your-"):
            raise DomainError(503, "MODEL_UNAVAILABLE", "Chưa cấu hình khóa mô hình AI.", True)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": settings.llm_temperature, "responseMimeType": "application/json"},
        }
        key_idx = 0
        max_attempts = max(3, len(key_pool))
        for attempt in range(max_attempts):
            current_key = key_pool[key_idx % len(key_pool)]
            headers = {"x-goog-api-key": current_key}
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=45)
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:
                status, code, retryable = _response_error(exc)
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429 and len(key_pool) > 1:
                    key_idx += 1
                    if key_idx < len(key_pool):
                        continue
                if retryable and attempt < max_attempts - 1:
                    time.sleep(0.3 * min(attempt + 1, 3))
                    continue
                raise DomainError(status, code, "Mô hình AI không khả dụng hoặc từ chối yêu cầu.", retryable) from None
    else:
        key = settings.openai_api_key if provider == "openai" else settings.gemini_api_key
        if not key or key.startswith("sk-your-"):
            raise DomainError(503, "MODEL_UNAVAILABLE", "Chưa cấu hình khóa mô hình AI.", True)
        url = chat_url(settings.gemini_base_url if provider == "openai_compatible" else settings.openai_base_url)
        headers = {"Authorization": f"Bearer {key}"}
        payload = {
            "model": model, "temperature": settings.llm_temperature,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        for attempt in range(3):
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=45)
                response.raise_for_status()
                break
            except httpx.HTTPError as exc:
                status, code, retryable = _response_error(exc)
                if retryable and attempt < 2:
                    time.sleep(0.3 * (attempt + 1))
                    continue
                raise DomainError(status, code, "Mô hình AI không khả dụng hoặc từ chối yêu cầu.", retryable) from None
    try:
        envelope = response.json()
        if provider == "gemini":
            content = "".join(part["text"] for part in envelope["candidates"][0]["content"]["parts"])
            usage = envelope.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount")
            completion_tokens = usage.get("candidatesTokenCount")
            total_tokens = usage.get("totalTokenCount")
            returned_model = envelope.get("modelVersion")
        else:
            content = envelope["choices"][0]["message"]["content"]
            usage = envelope.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")
            returned_model = envelope.get("model")
        if not isinstance(content, str):
            raise TypeError("string content required")
        fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", content.strip(), flags=re.DOTALL | re.IGNORECASE)
        data = json.loads(fenced.group(1) if fenced else content)
        if not isinstance(data, dict):
            raise ValueError("JSON object required")
    except (KeyError, IndexError, TypeError, ValueError):
        raise DomainError(422, "MODEL_OUTPUT_INVALID", "Mô hình trả kết quả không đúng schema.") from None
    return ModelResult(data, provider, model, returned_model, prompt_tokens, completion_tokens, total_tokens)
