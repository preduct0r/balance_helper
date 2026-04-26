from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.extractors.text import extract_text_from_html
from balance_fundraising.services.analysis import heuristic_analysis

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class AnalysisTests(unittest.TestCase):
    def test_vk_dobro_fixture(self) -> None:
        text = extract_text_from_html((FIXTURES / "vk_dobro.html").read_text(encoding="utf-8"))
        payload = heuristic_analysis("https://dobro.mail.ru/funds/registration/", text)
        self.assertEqual(payload["type"], "platform")
        self.assertIn("Отчетность фонда", payload["required_documents"])
        self.assertIn("Рекомендательные письма", payload["required_documents"])
        self.assertIsNone(payload["deadline"])

    def test_sbervmeste_deadline_fixture(self) -> None:
        text = extract_text_from_html((FIXTURES / "sbervmeste.html").read_text(encoding="utf-8"))
        payload = heuristic_analysis("https://example.org/sbervmeste", text)
        self.assertEqual(payload["deadline"], "2026-04-12")
        self.assertIn("Презентация фонда", payload["required_documents"])


if __name__ == "__main__":
    unittest.main()

