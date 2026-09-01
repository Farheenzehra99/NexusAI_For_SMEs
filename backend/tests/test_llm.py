"""Unit tests for the Gemini LLM client.

All network access is mocked — the suite never touches the live API
(also enforced session-wide by the ``_hermetic_llm`` conftest fixture).
Covers: configuration gating, request shape and key placement (header
auth, never in the URL), response parsing, and every documented
failure mode degrading to None.
"""

import io
import json
import urllib.error

from app.config import settings
from app.services import llm as llm_service


def _gemini_body(text: str) -> dict:
    """A minimal well-formed Gemini generateContent response body."""
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


class _FakeResponse:
    def __init__(self, body):
        self._body = json.dumps(body).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _patch_urlopen(monkeypatch, body):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["request"] = request
        captured["timeout"] = timeout
        return _FakeResponse(body)

    monkeypatch.setattr(llm_service.urllib.request, "urlopen", fake_urlopen)
    return captured


# ── configuration gate ───────────────────────────────────────────────────────

def test_is_llm_configured_reflects_key_presence(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert llm_service.is_llm_configured() is False
    monkeypatch.setattr(settings, "gemini_api_key", "some-key")
    assert llm_service.is_llm_configured() is True


def test_blank_key_is_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "   ")
    assert llm_service.is_llm_configured() is False


def test_not_configured_never_touches_network(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("network must not be touched when unconfigured")

    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(llm_service.urllib.request, "urlopen", no_network)
    assert llm_service._chat("system", "user") is None


# ── request shape & key placement ────────────────────────────────────────────

def test_success_extracts_text_from_candidates(monkeypatch):
    captured = _patch_urlopen(monkeypatch, _gemini_body("All good."))
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")

    assert llm_service._chat("SYS", "USER") == "All good."
    # Timeout from settings must be forwarded to the transport.
    assert captured["timeout"] == settings.llm_timeout_seconds


def test_key_sent_in_header_never_in_url(monkeypatch):
    captured = _patch_urlopen(monkeypatch, _gemini_body("ok"))
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")

    llm_service._chat("SYS", "USER")

    request = captured["request"]
    # urllib normalizes header names (casing varies by Python version) and
    # HTTP headers are case-insensitive — compare case-blind.
    sent = {k.lower(): v for k, v in request.headers.items()}
    assert sent.get("x-goog-api-key") == "test-key-123"
    # Security: the key must never leak into the URL (logs, errors, traces).
    assert "test-key-123" not in request.full_url
    assert "key=" not in request.full_url.lower()
    # The configured model must be the one actually addressed.
    assert settings.gemini_model in request.full_url


def test_payload_carries_system_instruction_and_user_content(monkeypatch):
    captured = {}
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")

    def fake_urlopen(request, timeout=None):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _FakeResponse(_gemini_body("ok"))

    monkeypatch.setattr(llm_service.urllib.request, "urlopen", fake_urlopen)

    llm_service._chat("SYS-PROMPT", "USER-CONTENT")

    payload = captured["payload"]
    assert payload["systemInstruction"]["parts"][0]["text"] == "SYS-PROMPT"
    assert payload["contents"][0]["parts"][0]["text"] == "USER-CONTENT"
    assert payload["contents"][0]["role"] == "user"
    # Deterministic-ish narration: low temperature, bounded output.
    assert payload["generationConfig"]["temperature"] == 0.2
    assert payload["generationConfig"]["maxOutputTokens"] > 0


# ── failure modes → None ────────────────────────────────────────────────────

def test_safety_blocked_generation_returns_none(monkeypatch):
    _patch_urlopen(
        monkeypatch,
        {"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []},
    )
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")
    assert llm_service._chat("SYS", "USER") is None


def test_empty_candidates_returns_none(monkeypatch):
    _patch_urlopen(monkeypatch, {"candidates": []})
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")
    assert llm_service._chat("SYS", "USER") is None


def test_missing_text_parts_return_none(monkeypatch):
    _patch_urlopen(monkeypatch, {"candidates": [{"content": {}}]})
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")
    assert llm_service._chat("SYS", "USER") is None


def test_non_dict_body_returns_none(monkeypatch):
    _patch_urlopen(monkeypatch, ["not", "a", "dict"])
    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")
    assert llm_service._chat("SYS", "USER") is None


def test_http_error_returns_none(monkeypatch):
    def raise_http_error(request, timeout=None):
        raise urllib.error.HTTPError(
            "https://generativelanguage.googleapis.com",
            429, "Too Many Requests", {}, io.BytesIO(b""),
        )

    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")
    monkeypatch.setattr(
        llm_service.urllib.request, "urlopen", raise_http_error
    )
    assert llm_service._chat("SYS", "USER") is None


def test_network_and_timeout_errors_return_none(monkeypatch):
    def raise_timeout(request, timeout=None):
        raise TimeoutError("provider too slow")

    monkeypatch.setattr(settings, "gemini_api_key", "test-key-123")
    monkeypatch.setattr(
        llm_service.urllib.request, "urlopen", raise_timeout
    )
    assert llm_service._chat("SYS", "USER") is None
