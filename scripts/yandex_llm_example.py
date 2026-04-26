from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app_defaults import DEFAULT_YANDEX_LLM_MODEL
from yandex_api import (
    build_yandex_completion_request,
    extract_yandex_completion_text,
    load_env_file,
)

COMPLETION_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
DEFAULT_SYSTEM_PROMPT = "You are a concise assistant. Answer in Russian."
DEFAULT_USER_PROMPT = "Кратко объясни, что делает этот пример скрипта."

load_env_file()


def require_api_key() -> str:
    api_key = os.getenv("YANDEX_API_KEY")
    if not api_key:
        raise RuntimeError("Set YANDEX_API_KEY in .env or the shell environment.")
    return api_key


def require_folder_id() -> str:
    folder_id = os.getenv("YANDEX_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("Set YANDEX_FOLDER_ID in .env or the shell environment.")
    return folder_id


def main() -> None:
    import requests

    folder_id = require_folder_id()
    request_body = build_yandex_completion_request(
        folder_id=folder_id,
        model=os.getenv("YANDEX_LLM_MODEL_URI", DEFAULT_YANDEX_LLM_MODEL),
        system_prompt=os.getenv("YANDEX_LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        user_prompt=os.getenv("YANDEX_LLM_USER_PROMPT", DEFAULT_USER_PROMPT),
        temperature=0.3,
        max_tokens=512,
    )

    response = requests.post(
        COMPLETION_URL,
        headers={
            "Authorization": f"Api-Key {require_api_key()}",
            "x-folder-id": folder_id,
        },
        json=request_body,
        timeout=60,
    )

    if not response.ok:
        print(f"Yandex LLM error {response.status_code}: {response.text}")
        response.raise_for_status()

    payload = response.json()
    print(extract_yandex_completion_text(payload))


if __name__ == "__main__":
    main()
