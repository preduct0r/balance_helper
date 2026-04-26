from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.clients.yandex_search import build_yandex_search_request, parse_yandex_search_raw_data


class YandexSearchTests(unittest.TestCase):
    def test_request_shape(self) -> None:
        body = build_yandex_search_request("прием заявок НКО")
        self.assertEqual(body["query"]["searchType"], "SEARCH_TYPE_RU")
        self.assertEqual(body["l10n"], "LOCALIZATION_RU")

    def test_parse_xml_results(self) -> None:
        raw = """
        <yandexsearch>
          <response>
            <results>
              <grouping>
                <group>
                  <doc>
                    <url>https://example.org/apply</url>
                    <title>Подать заявку</title>
                    <headline>НКО могут подать заявку</headline>
                    <passages><passage>Дедлайн скоро</passage></passages>
                  </doc>
                </group>
              </grouping>
            </results>
          </response>
        </yandexsearch>
        """
        results = parse_yandex_search_raw_data(raw)
        self.assertEqual(results[0].url, "https://example.org/apply")
        self.assertIn("Дедлайн", results[0].snippet)


if __name__ == "__main__":
    unittest.main()

