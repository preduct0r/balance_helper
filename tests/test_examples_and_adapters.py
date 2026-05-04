from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.google_sheets_store import GoogleSheetsStore
from balance_fundraising.domain import Application, FundWikiEntry

ROOT = Path(__file__).resolve().parents[1]


class ExampleAndAdapterTests(unittest.TestCase):
    def test_yandex_example_imports_without_running_main(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/yandex_llm_example.py"), run_name="__test__")
        self.assertIn("require_api_key", namespace)

    def test_google_sheets_init_does_not_recurse(self) -> None:
        spreadsheet = FakeSpreadsheet()
        store = GoogleSheetsStore("sheet", "service.json")
        with patch.object(store, "_open", return_value=spreadsheet):
            store.init_store()
        self.assertTrue(store._initialized)
        self.assertIn("FundWiki", spreadsheet.worksheets_by_title)

    def test_google_sheets_fund_wiki_upsert_supports_operator_fields(self) -> None:
        spreadsheet = FakeSpreadsheet()
        store = GoogleSheetsStore("sheet", "service.json")
        with patch.object(store, "_open", return_value=spreadsheet):
            store.init_store()
            store.upsert_fund_wiki_entry(
                FundWikiEntry(
                    key="impact",
                    value="100 участников",
                    source="Отчет",
                    owner="Анна",
                    review_state="approved",
                )
            )
            entries = {entry.key: entry for entry in store.list_fund_wiki()}
        self.assertEqual(entries["impact"].value, "100 участников")
        self.assertEqual(entries["impact"].owner, "Анна")

    def test_google_sheets_application_methods(self) -> None:
        spreadsheet = FakeSpreadsheet()
        store = GoogleSheetsStore("sheet", "service.json")
        with patch.object(store, "_open", return_value=spreadsheet):
            store.init_store()
            application = Application(id="app_1", opportunity_id="opp_1", owner="Анна")
            store.upsert_application(application)
            updated = store.update_application_fields("app_1", {"status": "waiting_response"})
            applications = store.list_applications()
        self.assertEqual(updated.status, "waiting_response")
        self.assertEqual(applications[0].owner, "Анна")


class FakeWorksheet:
    def __init__(self, title: str) -> None:
        self.title = title
        self.rows = []

    def get_all_records(self):
        if len(self.rows) <= 1:
            return []
        headers = self.rows[0]
        return [dict(zip(headers, row)) for row in self.rows[1:]]

    def row_values(self, index: int):
        if index <= len(self.rows):
            return self.rows[index - 1]
        return []

    def update(self, cell: str, values):
        if cell == "A1":
            if self.rows:
                self.rows[0] = values[0]
            else:
                self.rows.append(values[0])
            return
        if cell.startswith("A"):
            index = int(cell[1:]) - 1
            while len(self.rows) <= index:
                self.rows.append([])
            self.rows[index] = values[0]

    def append_row(self, values):
        self.rows.append(values)


class FakeSpreadsheet:
    def __init__(self) -> None:
        self.worksheets_by_title = {}

    def worksheets(self):
        return list(self.worksheets_by_title.values())

    def add_worksheet(self, title: str, rows: int, cols: int):
        worksheet = FakeWorksheet(title)
        self.worksheets_by_title[title] = worksheet
        return worksheet

    def worksheet(self, title: str):
        return self.worksheets_by_title[title]


if __name__ == "__main__":
    unittest.main()
