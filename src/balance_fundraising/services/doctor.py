from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping

from balance_fundraising.adapters.store_factory import StoreConfig
from balance_fundraising.services.structured_logging import build_logging_config, read_recent_error_events


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: str
    detail: str


def run_doctor(config: StoreConfig, *, env: Mapping[str, str] | None = None, root: Path | None = None) -> List[DoctorCheck]:
    values = env if env is not None else os.environ
    base = root or Path.cwd()
    checks = [
        _check_env_file(base),
        _check_dependency("requests", required=False),
        _check_dependency("bs4", required=False),
        _check_dependency("fastapi", required=True),
        _check_dependency("uvicorn", required=True),
        _check_dependency("multipart", required=True),
        _check_local_store(config) if config.backend == "local" else _check_google_store(config),
        _check_logs(values, base),
        _check_optional_env("YANDEX_API_KEY", values, "Yandex LLM/Search calls are disabled without it."),
        _check_optional_env("YANDEX_FOLDER_ID", values, "Yandex LLM/Search calls are disabled without it."),
        _check_optional_env("TELEGRAM_BOT_TOKEN", values, "Telegram polling is disabled without it."),
    ]
    return checks


def format_doctor_report(checks: Iterable[DoctorCheck]) -> str:
    lines = ["Диагностика сервиса:"]
    for check in checks:
        lines.append(f"- [{check.status.upper()}] {check.name}: {check.detail}")
    return "\n".join(lines)


def doctor_has_errors(checks: Iterable[DoctorCheck]) -> bool:
    return any(check.status == "error" for check in checks)


def _check_env_file(root: Path) -> DoctorCheck:
    env_path = root / ".env"
    if env_path.exists():
        return DoctorCheck(".env", "ok", "Файл .env найден.")
    return DoctorCheck(".env", "warn", "Файл .env не найден; можно использовать переменные окружения.")


def _check_dependency(module_name: str, *, required: bool) -> DoctorCheck:
    if importlib.util.find_spec(module_name):
        return DoctorCheck(f"dependency:{module_name}", "ok", "Зависимость доступна.")
    status = "error" if required else "warn"
    return DoctorCheck(f"dependency:{module_name}", status, "Зависимость не установлена.")


def _check_local_store(config: StoreConfig) -> DoctorCheck:
    path = Path(config.local_path)
    parent = path.parent
    if parent.exists() and os.access(parent, os.W_OK):
        return DoctorCheck("store:local", "ok", f"Local store доступен: {path}")
    if not parent.exists():
        return DoctorCheck("store:local", "warn", f"Папка будет создана при init-store: {parent}")
    return DoctorCheck("store:local", "error", f"Нет прав на запись в папку: {parent}")


def _check_google_store(config: StoreConfig) -> DoctorCheck:
    missing = []
    if not config.google_sheet_id:
        missing.append("GOOGLE_SHEET_ID")
    if not config.google_service_account_file:
        missing.append("GOOGLE_SERVICE_ACCOUNT_FILE")
    if missing:
        return DoctorCheck("store:google", "error", "Не хватает: " + ", ".join(missing))
    if importlib.util.find_spec("gspread") is None:
        return DoctorCheck("store:google", "error", "Не установлена зависимость gspread.")
    return DoctorCheck("store:google", "ok", "Google store настроен локально; сетевой доступ не проверялся.")


def _check_logs(env: Mapping[str, str], root: Path) -> DoctorCheck:
    config = build_logging_config(env=env, root=root)
    parent = config.log_file.parent
    level = env.get("BALANCE_LOG_LEVEL", config.level).upper()
    recent_errors = read_recent_error_events(config.log_file, limit=3)
    detail = f"{config.log_file}; BALANCE_LOG_LEVEL={level}; recent_errors={len(recent_errors)}"
    if parent.exists() and os.access(parent, os.W_OK):
        return DoctorCheck("logs:jsonl", "ok", detail)
    if not parent.exists():
        return DoctorCheck("logs:jsonl", "warn", detail + f"; папка будет создана: {parent}")
    return DoctorCheck("logs:jsonl", "error", f"Нет прав на запись в папку логов: {parent}")


def _check_optional_env(name: str, env: Mapping[str, str], missing_detail: str) -> DoctorCheck:
    if env.get(name):
        return DoctorCheck(f"env:{name}", "ok", "Переменная задана.")
    return DoctorCheck(f"env:{name}", "warn", missing_detail)
