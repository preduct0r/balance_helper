from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.google_sheets_store import GoogleSheetsStore
from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.adapters.store_factory import build_store_config, create_store
from balance_fundraising.cli import main as cli_main
from balance_fundraising.services.doctor import doctor_has_errors, format_doctor_report, run_doctor

ROOT = Path(__file__).resolve().parents[1]


class StoreFactoryAndDoctorTests(unittest.TestCase):
    def test_store_factory_selects_local_by_default(self) -> None:
        config = build_store_config(env={})
        self.assertEqual(config.backend, "local")
        self.assertIsInstance(create_store(config), LocalJsonStore)

    def test_store_factory_selects_google_with_required_config(self) -> None:
        config = build_store_config(
            backend="google",
            google_sheet_id="sheet-id",
            google_service_account_file="service-account.json",
            env={},
        )
        store = create_store(config)
        self.assertIsInstance(store, GoogleSheetsStore)
        self.assertEqual(store.spreadsheet_id, "sheet-id")

    def test_store_factory_rejects_google_without_config(self) -> None:
        config = build_store_config(backend="google", env={})
        with self.assertRaises(RuntimeError):
            create_store(config)

    def test_doctor_warns_without_failing_local_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = build_store_config(local_path=str(Path(tmp) / "store.json"), env={})
            checks = run_doctor(config, env={}, root=Path(tmp))
        self.assertFalse(doctor_has_errors(checks))
        report = format_doctor_report(checks)
        self.assertIn("Диагностика сервиса", report)
        self.assertIn("YANDEX_API_KEY", report)

    def test_doctor_errors_for_misconfigured_google_mode(self) -> None:
        config = build_store_config(backend="google", env={})
        checks = run_doctor(config, env={}, root=ROOT)
        self.assertTrue(doctor_has_errors(checks))
        self.assertIn("GOOGLE_SHEET_ID", format_doctor_report(checks))

    def test_cli_doctor_runs_without_creating_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = cli_main(["--store", str(Path(tmp) / "store.json"), "doctor"])
        self.assertEqual(exit_code, 0)
        self.assertIn("Диагностика сервиса", output.getvalue())

    def test_cli_uses_selected_store_backend(self) -> None:
        fake_store = FakeStore()
        with patch("balance_fundraising.cli.create_store", return_value=fake_store) as create_store_mock:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = cli_main(["--store-backend", "google", "init-store"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(fake_store.initialized)
        self.assertEqual(create_store_mock.call_args.args[0].backend, "google")
        self.assertIn("Initialized google store", output.getvalue())

    def test_cli_seed_demo_populates_local_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "store.json"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = cli_main(["--store", str(store_path), "seed-demo"])
            store = LocalJsonStore(store_path)
            opportunities = store.list_opportunities()
        self.assertEqual(exit_code, 0)
        self.assertIn("Seeded demo", output.getvalue())
        self.assertGreaterEqual(len(opportunities), 5)

    def test_cli_application_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store_path = Path(tmp) / "store.json"
            store = LocalJsonStore(store_path)
            store.init_store()
            opportunity = store.list_opportunities()
            self.assertEqual(opportunity, [])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                created = cli_main(["--store", str(store_path), "add-link", "https://example.org/app"])
            self.assertEqual(created, 0)
            opportunity_id = LocalJsonStore(store_path).list_opportunities()[0].id
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = cli_main(["--store", str(store_path), "application-create", opportunity_id])
            application_id = output.getvalue().strip()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status_code = cli_main(["--store", str(store_path), "application-status", application_id, "waiting_response"])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                list_code = cli_main(["--store", str(store_path), "applications"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(status_code, 0)
        self.assertEqual(list_code, 0)
        self.assertIn("waiting_response", output.getvalue())


class FakeStore:
    def __init__(self) -> None:
        self.initialized = False

    def init_store(self) -> None:
        self.initialized = True


if __name__ == "__main__":
    unittest.main()
