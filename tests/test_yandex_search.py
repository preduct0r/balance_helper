from __future__ import annotations

import base64
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.app_defaults import YANDEX_SEARCH_URL
from balance_fundraising.clients.yandex_search import YandexSearchClient, build_yandex_search_request, parse_yandex_search_raw_data


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

    def test_parse_base64_encoded_xml_results(self) -> None:
        raw_xml = """
        <yandexsearch>
          <response>
            <results>
              <grouping>
                <group>
                  <doc>
                    <url>https://example.org/blog</url>
                    <title>Психологический блог</title>
                    <passages><passage>Блог о ментальном здоровье</passage></passages>
                  </doc>
                </group>
              </grouping>
            </results>
          </response>
        </yandexsearch>
        """
        raw_data = base64.b64encode(raw_xml.encode("utf-8")).decode("ascii")
        results = parse_yandex_search_raw_data(raw_data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://example.org/blog")
        self.assertIn("ментальном здоровье", results[0].snippet)

    def test_client_uses_default_endpoint_when_env_is_empty(self) -> None:
        with patch.dict("os.environ", {"YANDEX_SEARCH_ENDPOINT": ""}):
            client = YandexSearchClient(api_key="key", folder_id="folder")
        self.assertEqual(client.endpoint, YANDEX_SEARCH_URL)


if __name__ == "__main__":
    unittest.main()
