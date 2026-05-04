from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from balance_fundraising.adapters.google_sheets_store import GoogleSheetsStore
from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.app_defaults import DEFAULT_STORE_PATH


@dataclass(frozen=True)
class StoreConfig:
    backend: str = "local"
    local_path: str = DEFAULT_STORE_PATH
    google_sheet_id: Optional[str] = None
    google_service_account_file: Optional[str] = None


def build_store_config(
    *,
    backend: Optional[str] = None,
    local_path: Optional[str] = None,
    google_sheet_id: Optional[str] = None,
    google_service_account_file: Optional[str] = None,
    env: Mapping[str, str] | None = None,
) -> StoreConfig:
    values = env if env is not None else os.environ
    selected_backend = (backend or values.get("BALANCE_STORE_BACKEND") or "local").lower()
    if selected_backend not in {"local", "google"}:
        raise ValueError("Store backend must be one of: local, google")
    return StoreConfig(
        backend=selected_backend,
        local_path=local_path or values.get("BALANCE_STORE_PATH") or DEFAULT_STORE_PATH,
        google_sheet_id=google_sheet_id or values.get("GOOGLE_SHEET_ID"),
        google_service_account_file=google_service_account_file or values.get("GOOGLE_SERVICE_ACCOUNT_FILE"),
    )


def create_store(config: StoreConfig):
    if config.backend == "local":
        return LocalJsonStore(config.local_path)
    if not config.google_sheet_id:
        raise RuntimeError("Set GOOGLE_SHEET_ID to use the google store backend.")
    if not config.google_service_account_file:
        raise RuntimeError("Set GOOGLE_SERVICE_ACCOUNT_FILE to use the google store backend.")
    return GoogleSheetsStore(config.google_sheet_id, config.google_service_account_file)
