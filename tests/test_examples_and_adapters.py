from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.google_sheets_store import GoogleSheetsStore

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

