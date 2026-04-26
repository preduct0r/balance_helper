from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


def load_env_file(path: str | os.PathLike[str] = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def build_model_uri(folder_id: str, model: str) -> str:
    if model.startswith("gpt://"):
        return model
    return f"gpt://{folder_id}/{model}"


def build_yandex_completion_request(
    *,
    folder_id: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 512,
) -> Dict[str, Any]:
    return {
        "modelUri": build_model_uri(folder_id, model),
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": str(max_tokens),
        },
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_prompt},
        ],
    }


def extract_yandex_completion_text(payload: Dict[str, Any]) -> str:
    alternatives = payload.get("result", {}).get("alternatives", [])
    if not alternatives:
        return ""
    message = alternatives[0].get("message", {})
    return message.get("text", "")


def require_env(name: str, hint: Optional[str] = None) -> str:
    value = os.getenv(name)
    if not value:
        suffix = f" {hint}" if hint else ""
        raise RuntimeError(f"Set {name} in .env or the shell environment.{suffix}")
    return value

