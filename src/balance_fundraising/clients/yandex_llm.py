from __future__ import annotations

import os

from balance_fundraising.app_defaults import DEFAULT_YANDEX_LLM_MODEL, YANDEX_COMPLETION_URL
from balance_fundraising.yandex_api import (
    build_yandex_completion_request,
    extract_yandex_completion_text,
    load_env_file,
    require_env,
)


class YandexLLMClient:
    def __init__(self, *, api_key: str | None = None, folder_id: str | None = None, model: str | None = None) -> None:
        load_env_file()
        self.api_key = api_key or require_env("YANDEX_API_KEY")
        self.folder_id = folder_id or require_env("YANDEX_FOLDER_ID")
        self.model = model or os.getenv("YANDEX_LLM_MODEL_URI", DEFAULT_YANDEX_LLM_MODEL)

    def complete(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 2048) -> str:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install requests to call Yandex LLM: pip install -r requirements.txt") from exc

        body = build_yandex_completion_request(
            folder_id=self.folder_id,
            model=self.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response = requests.post(
            YANDEX_COMPLETION_URL,
            headers={
                "Authorization": f"Api-Key {self.api_key}",
                "x-folder-id": self.folder_id,
            },
            json=body,
            timeout=60,
        )
        if not response.ok:
            raise RuntimeError(f"Yandex LLM error {response.status_code}: {response.text}")
        return extract_yandex_completion_text(response.json())

