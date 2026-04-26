from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.extractors.structured import parse_analysis_json


class StructuredExtractorTests(unittest.TestCase):
    def test_invalid_json_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_analysis_json("not json")

    def test_missing_fields_are_marked(self) -> None:
        payload = parse_analysis_json('{"name": "VK Добро"}')
        self.assertEqual(payload["name"], "VK Добро")
        self.assertEqual(payload["type"], "unknown")
        self.assertIn("Поле не найдено в ответе LLM: organization", payload["missing_info"])


if __name__ == "__main__":
    unittest.main()

