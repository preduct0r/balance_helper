from __future__ import annotations

import json
import os
import re
import sys
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
DEFAULT_LOG_FILE = "logs/app.jsonl"

_CONFIG: "LoggingConfig | None" = None
_LOCK = threading.Lock()


@dataclass(frozen=True)
class LoggingConfig:
    log_file: Path
    level: str = "INFO"
    to_console: bool = False


def build_logging_config(*, env: Mapping[str, str] | None = None, root: Path | None = None) -> LoggingConfig:
    values = env if env is not None else os.environ
    base = root or Path.cwd()
    log_file = Path(values.get("BALANCE_LOG_FILE", DEFAULT_LOG_FILE))
    if not log_file.is_absolute():
        log_file = base / log_file
    level = values.get("BALANCE_LOG_LEVEL", "INFO").upper()
    if level not in LEVELS:
        level = "INFO"
    to_console = values.get("BALANCE_LOG_TO_CONSOLE", "0").lower() in {"1", "true", "yes", "on"}
    return LoggingConfig(log_file=log_file, level=level, to_console=to_console)


def configure_logging(config: LoggingConfig | None = None) -> LoggingConfig:
    global _CONFIG
    _CONFIG = config or build_logging_config()
    _CONFIG.log_file.parent.mkdir(parents=True, exist_ok=True)
    return _CONFIG


def current_logging_config() -> LoggingConfig:
    if _CONFIG is None:
        return configure_logging()
    return _CONFIG


def log_event(event: str, message: str = "", *, level: str = "INFO", **fields: Any) -> None:
    config = current_logging_config()
    normalized_level = level.upper()
    if normalized_level not in LEVELS:
        normalized_level = "INFO"
    if LEVELS[normalized_level] < LEVELS[config.level]:
        return
    record = {
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "level": normalized_level,
        "event": sanitize_log_value(event),
        "message": sanitize_log_value(message),
    }
    for key, value in fields.items():
        if value is not None:
            record[key] = sanitize_log_value(value)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with _LOCK:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        with config.log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        if config.to_console:
            print(line, file=sys.stderr)


def exception_traceback(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def read_recent_error_events(log_file: Path | str, *, limit: int = 5) -> list[dict[str, Any]]:
    path = Path(log_file)
    if not path.exists():
        return []
    rows = []
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("level") == "ERROR" or str(row.get("event", "")).endswith(".error"):
            rows.append(row)
        if len(rows) >= limit:
            break
    return list(reversed(rows))


def sanitize_log_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, Mapping):
        return {str(key): sanitize_log_value(item) for key, item in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return [sanitize_log_value(item) for item in value]
    return value


def _sanitize_text(value: str) -> str:
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[скрыто]", value)
    text = _EMAIL_RE.sub("[email]", text)
    text = _PHONE_RE.sub("[phone]", text)
    return text


_SECRET_ASSIGNMENT_RE = re.compile(
    r"\b(YANDEX_API_KEY|YANDEX_FOLDER_ID|TELEGRAM_BOT_TOKEN|GOOGLE_SERVICE_ACCOUNT_FILE|GOOGLE_SHEET_ID|API_KEY|TOKEN|SECRET|PASSWORD)\s*[:=]\s*([^\s,;]+)",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
