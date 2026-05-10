"""Tests for LLMClient JSON parsing behaviour."""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import BaseModel
from typing import Optional

from core.llm_client import LLMClient


class _SimpleSchema(BaseModel):
    value: str
    count: Optional[int] = None


PLAIN_JSON = '{"value": "hello", "count": 42}'
FENCED_JSON = '```json\n{"value": "hello", "count": 42}\n```'
FENCED_NO_LANG = '```\n{"value": "hello", "count": 42}\n```'
EMPTY_STRING = ""


# ---------------------------------------------------------------------------
# Hypothesis 1: Yandex returns JSON wrapped in markdown fences
# ---------------------------------------------------------------------------

class TestFencedJsonParsing:
    """Verify that complete_structured handles markdown-fenced JSON responses."""

    def _make_client(self, raw_response: str) -> LLMClient:
        client = LLMClient(provider="yandex", model="gpt-4o-mini")
        client._yandex_chat = MagicMock(return_value=raw_response)
        return client

    def test_plain_json_parses_ok(self):
        client = self._make_client(PLAIN_JSON)
        result = client.complete_structured(
            system_prompt="sys",
            user_prompt="user",
            schema=_SimpleSchema,
            schema_hint_explicit="",
        )
        assert result["value"] == "hello"
        assert result["count"] == 42

    def test_fenced_json_with_lang_tag_parses_ok(self):
        client = self._make_client(FENCED_JSON)
        result = client.complete_structured(
            system_prompt="sys",
            user_prompt="user",
            schema=_SimpleSchema,
            schema_hint_explicit="",
        )
        assert result["value"] == "hello"
        assert result["count"] == 42

    def test_fenced_json_no_lang_tag_parses_ok(self):
        client = self._make_client(FENCED_NO_LANG)
        result = client.complete_structured(
            system_prompt="sys",
            user_prompt="user",
            schema=_SimpleSchema,
            schema_hint_explicit="",
        )
        assert result["value"] == "hello"
        assert result["count"] == 42


# ---------------------------------------------------------------------------
# Hypothesis 2: Yandex retry loses correction context
# ---------------------------------------------------------------------------

class TestYandexRetryContext:
    """Verify that the retry call actually passes the correction prompt."""

    def test_retry_uses_last_user_message(self):
        """
        _chat for Yandex uses next(...) on the original messages list,
        so appended retry messages are silently ignored.
        This test captures the call args on both attempts.
        """
        call_args = []

        def fake_yandex_chat(system_prompt, user_prompt, temperature=0.0):
            call_args.append(user_prompt)
            # First call: return fenced (bad) JSON to trigger retry
            # Second call: return something (also bad) to observe what was passed
            return FENCED_JSON

        client = LLMClient(provider="yandex", model="gpt-4o-mini")
        client._yandex_chat = fake_yandex_chat

        with pytest.raises(Exception):
            client.complete_structured(
                system_prompt="sys",
                user_prompt="original user prompt",
                schema=_SimpleSchema,
                schema_hint_explicit="",
            )

        assert len(call_args) == 2, "Expected exactly 2 LLM calls (first + retry)"
        assert call_args[0] == "original user prompt"
        assert "Ошибка парсинга" in call_args[1], (
            "Retry must pass the correction message, not the original prompt"
        )
