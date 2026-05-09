from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.app_defaults import DEFAULT_YANDEX_LLM_MODEL
from balance_fundraising.clients.yandex_llm import YandexLLMClient
from balance_fundraising.yandex_api import build_yandex_completion_request, extract_yandex_completion_text


class YandexApiTests(unittest.TestCase):
    def test_completion_request_shape(self) -> None:
        body = build_yandex_completion_request(
            folder_id="folder",
            model="yandexgpt/latest",
            system_prompt="system",
            user_prompt="user",
            temperature=0.3,
            max_tokens=512,
        )
        self.assertEqual(body["modelUri"], "gpt://folder/yandexgpt/latest")
        self.assertEqual(body["completionOptions"]["maxTokens"], "512")
        self.assertEqual(body["messages"][0], {"role": "system", "text": "system"})
        self.assertEqual(body["messages"][1], {"role": "user", "text": "user"})

    def test_extract_completion_text(self) -> None:
        payload = {"result": {"alternatives": [{"message": {"text": "ответ"}}]}}
        self.assertEqual(extract_yandex_completion_text(payload), "ответ")

    def test_llm_client_uses_default_model_when_env_is_empty(self) -> None:
        with patch.dict("os.environ", {"YANDEX_LLM_MODEL_URI": ""}):
            client = YandexLLMClient(api_key="key", folder_id="folder")
        self.assertEqual(client.model, DEFAULT_YANDEX_LLM_MODEL)


if __name__ == "__main__":
    unittest.main()
