from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


if __name__ == "__main__":
    unittest.main()

