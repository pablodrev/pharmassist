"""
LLM client abstraction over Ollama and Yandex Cloud.
Provides structured JSON output with Pydantic validation.
"""

from __future__ import annotations
import json
import logging
import os
from typing import Optional, Type, TypeVar

import requests
from pydantic import BaseModel, ValidationError

try:
    import openai
except ImportError:  # pragma: no cover
    openai = None

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "yandexgpt-lite"  # Yandex Cloud model
DEFAULT_PROVIDER = "yandex"  # Use Yandex Cloud by default, Ollama only on reanalyze
FALLBACK_MODEL = "phi3"    # even lighter (~2GB)


class LLMClient:
    """
    Wrapper around Ollama /api/chat and Yandex Cloud Responses API.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        provider: str = DEFAULT_PROVIDER,
        base_url: str = OLLAMA_BASE_URL,
        yandex_api_key: Optional[str] = None,
        yandex_folder_id: Optional[str] = None,
    ):
        self.model = model
        self.provider = provider.lower()
        self.base_url = base_url
        self.yandex_api_key = yandex_api_key or os.getenv("YANDEX_CLOUD_API_KEY")
        self.yandex_folder_id = yandex_folder_id or os.getenv("YANDEX_CLOUD_FOLDER")
        self._yandex_client = None

    def _is_yandex(self) -> bool:
        return self.provider == "yandex"

    def _format_yandex_model(self) -> str:
        if self.model.startswith("gpt://"):
            return self.model
        if not self.yandex_folder_id:
            raise RuntimeError(
                "YANDEX_CLOUD_FOLDER не задан. Установите `YANDEX_CLOUD_FOLDER` или передайте `yandex_folder_id`."
            )
        return f"gpt://{self.yandex_folder_id}/{self.model}"

    def _get_yandex_client(self):
        if openai is None:
            raise RuntimeError(
                "Пакет `openai` не установлен. Установите его: `pip install openai`."
            )
        if self._yandex_client is None:
            if not self.yandex_api_key:
                raise RuntimeError(
                    "YANDEX_CLOUD_API_KEY не задан. Установите `YANDEX_CLOUD_API_KEY` или передайте `yandex_api_key`."
                )
            if not self.yandex_folder_id:
                raise RuntimeError(
                    "YANDEX_CLOUD_FOLDER не задан. Установите `YANDEX_CLOUD_FOLDER` или передайте `yandex_folder_id`."
                )
            self._yandex_client = openai.OpenAI(
                api_key=self.yandex_api_key,
                base_url="https://ai.api.cloud.yandex.net/v1",
                project=self.yandex_folder_id,
            )
        return self._yandex_client

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            newline = text.find("\n")
            text = text[newline + 1:] if newline != -1 else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        return text.strip()

    def _yandex_chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
        client = self._get_yandex_client()
        model_name = self._format_yandex_model()
        response = client.responses.create(
            model=model_name,
            temperature=temperature,
            instructions=system_prompt,
            input=user_prompt,
            max_output_tokens=2000,
        )
        status = getattr(response, "status", None)
        if status == "failed":
            error = getattr(response, "error", None)
            msg = getattr(error, "message", str(error)) if error else "unknown error"
            raise RuntimeError(f"Yandex Cloud response failed: {msg}")

        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text
        if isinstance(response, dict):
            return response.get("output_text", "") or ""
        if hasattr(response, "to_dict"):
            data = response.to_dict()
            return data.get("output_text", "") or ""
        raise RuntimeError("Не удалось получить текст ответа от Yandex Cloud.")

    def _chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        if self._is_yandex():
            system_prompt = next((m["content"] for m in messages if m["role"] == "system"), "")
            user_prompt = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
            return self._yandex_chat(system_prompt, user_prompt, temperature)

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
            "format": "json",
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=600,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Не удалось подключиться к Ollama. "
                "Убедитесь, что ollama запущен: `ollama serve`"
            )

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Type[T],
        schema_hint_explicit: str,
        temperature: float = 0.0,
    ) -> T:
        if schema_hint_explicit:
            schema_hint = schema_hint_explicit
        else:
            schema_hint = json.dumps(
                schema.model_json_schema()["properties"], ensure_ascii=False, indent=2
            )
        # print("SCHEMA HINT: ", schema_hint)
        full_system = (
            f"{system_prompt}\n\n"
            f"ВАЖНО: Отвечай СТРОГО в формате JSON, соответствующем следующей схеме:\n"
            f"```json\n{schema_hint}\n```\n"
            f"Никакого текста вне JSON. Все строки на русском языке."
        )
        logger.info(
            "LLM call: provider=%s model=%s user_prompt_len=%d preview=%r",
            self.provider, self.model, len(user_prompt), user_prompt[:400],
        )
        messages = [
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt},
        ]
        raw = self._chat(messages, temperature)
        logger.info("LLM raw output (len=%d): %r", len(raw), raw[:500])
        stripped = self._strip_json_fences(raw)
        logger.info("After fence-strip (len=%d): %r", len(stripped), stripped[:500])
        try:
            data = json.loads(stripped)
            return data
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("First parse failed: %s. Retrying with error hint.", e)
            # Для Yandex _chat берёт только последнее user-сообщение, поэтому
            # при повторной попытке передаём ВЕСЬ оригинальный запрос + подсказку об ошибке.
            # Это предотвращает ситуацию, когда модель получает только сообщение об ошибке
            # и возвращает JSON с null-полями, не видя исходного документа.
            retry_user = (
                f"{user_prompt}\n\n"
                f"Предыдущий ответ не является валидным JSON (ошибка: {e}). "
                "Верни ТОЛЬКО валидный JSON по схеме выше, без дополнительного текста."
            )
            retry_messages = [
                {"role": "system", "content": full_system},
                {"role": "user", "content": retry_user},
            ]
            raw2 = self._chat(retry_messages, temperature)
            logger.info("LLM retry raw output (len=%d): %r", len(raw2), raw2[:500])
            stripped2 = self._strip_json_fences(raw2)
            logger.info("After fence-strip retry (len=%d): %r", len(stripped2), stripped2[:500])
            return json.loads(stripped2)

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        if self._is_yandex():
            return self._yandex_chat(system_prompt, user_prompt, temperature=0.1)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    def is_available(self) -> bool:
        if self._is_yandex():
            return bool(openai is not None and self.yandex_api_key and self.yandex_folder_id)
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
