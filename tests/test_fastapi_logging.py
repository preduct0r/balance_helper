from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.fastapi_app import create_fastapi_app
from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.services.structured_logging import (
    LoggingConfig,
    configure_logging,
    log_event,
    read_recent_error_events,
    sanitize_log_value,
)


class FastApiLoggingTests(unittest.TestCase):
    def test_sanitizer_masks_secrets_email_and_phone(self) -> None:
        text = "YANDEX_API_KEY=secret123 contact test@example.org phone +7 999 123-45-67"
        sanitized = sanitize_log_value(text)
        self.assertIn("YANDEX_API_KEY=[скрыто]", sanitized)
        self.assertIn("[email]", sanitized)
        self.assertIn("[phone]", sanitized)
        self.assertNotIn("secret123", sanitized)
        self.assertNotIn("test@example.org", sanitized)
        self.assertNotIn("+7 999 123-45-67", sanitized)

    def test_jsonl_logger_writes_valid_sanitized_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "app.jsonl"
            configure_logging(LoggingConfig(log_file=log_path, level="INFO", to_console=False))
            log_event(
                "store.update",
                "Updated YANDEX_API_KEY=secret123",
                request_id="req-1",
                entity_type="opportunity",
                entity_id="opp-1",
                details="operator@example.org +7 999 123-45-67",
            )
            row = json.loads(log_path.read_text(encoding="utf-8").strip())
        self.assertEqual(row["event"], "store.update")
        self.assertEqual(row["level"], "INFO")
        self.assertEqual(row["request_id"], "req-1")
        self.assertEqual(row["entity_id"], "opp-1")
        self.assertIn("timestamp", row)
        self.assertNotIn("secret123", json.dumps(row, ensure_ascii=False))
        self.assertNotIn("operator@example.org", json.dumps(row, ensure_ascii=False))
        self.assertNotIn("+7 999 123-45-67", json.dumps(row, ensure_ascii=False))

    def test_fastapi_app_preserves_get_post_flow_and_logs_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "app.jsonl"
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = create_fastapi_app(store, log_config=LoggingConfig(log_file=log_path, level="INFO", to_console=False))
            client = TestClient(app)
            root = client.get("/")
            response = client.post("/opportunities", data={"url": "https://example.org/platform"}, follow_redirects=False)
            rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(root.status_code, 200)
        self.assertIn("Рабочий стол фандрайзинга", root.text)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["location"].startswith("/opportunities/"))
        request_rows = [row for row in rows if row["event"] == "web.request"]
        self.assertGreaterEqual(len(request_rows), 2)
        self.assertEqual(request_rows[0]["method"], "GET")
        self.assertEqual(request_rows[0]["path"], "/")
        self.assertIn("duration_ms", request_rows[0])
        self.assertTrue(all(row.get("request_id") for row in request_rows))

    def test_fastapi_exception_path_logs_sanitized_stack_trace(self) -> None:
        class BrokenWebApp:
            def render(self, path: str):
                raise RuntimeError("YANDEX_API_KEY=secret123 operator@example.org")

            def post(self, path: str, form):
                raise RuntimeError("unused")

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "app.jsonl"
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = create_fastapi_app(
                store,
                web_app=BrokenWebApp(),
                log_config=LoggingConfig(log_file=log_path, level="INFO", to_console=False),
            )
            response = TestClient(app).get("/broken")
            rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            error_rows = [row for row in rows if row["event"] == "web.error"]
        self.assertEqual(response.status_code, 500)
        self.assertIn("Ошибка", response.text)
        self.assertEqual(len(error_rows), 1)
        encoded = json.dumps(error_rows[0], ensure_ascii=False)
        self.assertIn("RuntimeError", encoded)
        self.assertNotIn("secret123", encoded)
        self.assertNotIn("operator@example.org", encoded)

    def test_recent_error_events_reads_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "app.jsonl"
            configure_logging(LoggingConfig(log_file=log_path, level="INFO", to_console=False))
            log_event("web.request", "ok", level="INFO")
            log_event("web.error", "first", level="ERROR")
            log_event("radar.error", "second", level="ERROR")
            errors = read_recent_error_events(log_path, limit=1)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["message"], "second")


if __name__ == "__main__":
    unittest.main()
