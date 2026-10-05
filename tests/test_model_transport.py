"""Provider transport contract without spending API calls or exposing credentials."""

import httpx
import pytest

from src.ai.transport import complete_json
from src.config import Settings
from src.vmec import DomainError


def settings(**values):
    # _env_file=None does not disable os.environ; explicitly isolate the key pool.
    defaults = {"openai_api_key": "", "gemini_api_key": ""}
    defaults.update({f"gemini_api_key_{index}": "" for index in range(2, 9)})
    return Settings(_env_file=None, **{**defaults, **values})


@pytest.fixture(autouse=True)
def reset_gemini_rotation(monkeypatch):
    monkeypatch.setattr("src.ai.transport._gemini_key_index", 0)


def recording_post(monkeypatch, payload):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    return calls


@pytest.mark.parametrize("base", ["http://localhost:8317", "http://localhost:8317/v1/"])
def test_custom_proxy_uses_chat_completions_and_its_alias(monkeypatch, base):
    calls = recording_post(monkeypatch, {
        "model": "gemini-3.6-flash", "choices": [{"message": {"content": '{"ok":true}'}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15},
    })
    result = complete_json("system", "user", settings(
        model_provider="openai_compatible", gemini_base_url=base,
        gemini_api_key="secret", model_name="gemini-3.6-flash-high",
    ))
    assert result.data == {"ok": True}
    assert result.requested_model == "gemini-3.6-flash-high"
    assert result.returned_model == "gemini-3.6-flash"
    assert result.prompt_tokens == 12
    assert calls[0][0] == "http://localhost:8317/v1/chat/completions"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer secret"
    assert calls[0][1]["json"]["model"] == "gemini-3.6-flash-high"


def test_official_openai_endpoint(monkeypatch):
    calls = recording_post(monkeypatch, {"choices": [{"message": {"content": '{"ok":1}'}}]})
    result = complete_json("system", "user", settings(
        model_provider="openai", openai_api_key="openai-secret", model_name="gpt-test",
    ))
    assert result.data == {"ok": 1}
    assert calls[0][0] == "https://api.openai.com/v1/chat/completions"
    assert calls[0][1]["headers"]["Authorization"] == "Bearer openai-secret"


def test_official_gemini_native_endpoint(monkeypatch):
    calls = recording_post(monkeypatch, {
        "modelVersion": "gemini-test-001",
        "candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}],
        "usageMetadata": {"promptTokenCount": 6, "candidatesTokenCount": 2, "totalTokenCount": 8},
    })
    result = complete_json("system", "user", settings(
        model_provider="gemini", gemini_api_key="gemini-secret", model_name="gemini-test",
    ))
    assert result.data == {"ok": True}
    assert result.returned_model == "gemini-test-001"
    assert result.completion_tokens == 2
    assert calls[0][0] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"
    assert calls[0][1]["headers"]["x-goog-api-key"] == "gemini-secret"
    assert calls[0][1]["json"]["generationConfig"]["responseMimeType"] == "application/json"


def test_malformed_response_is_distinct_and_does_not_echo_secret(monkeypatch):
    recording_post(monkeypatch, {"choices": [{"message": {"content": "not JSON"}}]})
    with pytest.raises(DomainError) as error:
        complete_json("system", "user", settings(
            model_provider="openai_compatible", gemini_base_url="http://localhost:8317",
            gemini_api_key="highly-secret", model_name="model",
        ))
    assert error.value.code == "MODEL_OUTPUT_INVALID"
    assert "highly-secret" not in str(error.value)


def test_custom_proxy_accepts_a_single_json_code_fence(monkeypatch):
    recording_post(monkeypatch, {"choices": [{"message": {"content": '```json\n{"assertions": []}\n```'}}]})
    result = complete_json("system", "user", settings(
        model_provider="openai_compatible", gemini_base_url="http://localhost:8317",
        gemini_api_key="secret", model_name="model",
    ))
    assert result.data == {"assertions": []}


def test_missing_key_stops_before_http(monkeypatch):
    def no_call(*args, **kwargs):
        raise AssertionError("HTTP was called")

    monkeypatch.setattr(httpx, "post", no_call)
    with pytest.raises(DomainError) as error:
        complete_json("system", "user", settings(model_provider="openai"))
    assert error.value.code == "MODEL_UNAVAILABLE"


def test_retryable_server_error_is_bounded_and_permission_error_is_distinct(monkeypatch):
    attempts = []
    monkeypatch.setattr("src.ai.transport.time.sleep", lambda seconds: None)

    def post(url, **kwargs):
        attempts.append(url)
        status = 503 if len(attempts) < 3 else 200
        return httpx.Response(status, json={"choices": [{"message": {"content": "{}"}}]},
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    configured = settings(model_provider="openai", openai_api_key="secret")
    assert complete_json("system", "user", configured).data == {}
    assert len(attempts) == 3

    def denied(url, **kwargs):
        attempts.append(url)
        return httpx.Response(403, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", denied)
    with pytest.raises(DomainError) as error:
        complete_json("system", "user", configured)
    assert error.value.code == "MODEL_PERMISSION_DENIED"
    assert len(attempts) == 4


def test_gemini_rotates_and_failover_on_429(monkeypatch):
    used_keys = []

    def mock_post(url, headers, json, timeout):
        key = headers.get("x-goog-api-key")
        used_keys.append(key)
        if key == "key-1":
            # Simulate 429 Rate Limit on first key
            request = httpx.Request("POST", url)
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)
        return httpx.Response(200, json={
            "modelVersion": "gemini-3.5-flash-lite",
            "candidates": [{"content": {"parts": [{"text": '{"result": "ok"}'}]}}],
            "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2, "totalTokenCount": 7},
        }, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", mock_post)

    cfg = settings(
        model_provider="gemini",
        gemini_api_key="key-1",
        gemini_api_key_2="key-2",
        gemini_api_key_3="key-3",
    )
    res = complete_json("system", "user", cfg)
    assert res.data == {"result": "ok"}
    # key-1 was tried first, hit 429, failover to key-2 succeeded!
    assert "key-1" in used_keys
    assert "key-2" in used_keys

