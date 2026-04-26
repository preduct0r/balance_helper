from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List

from balance_fundraising.app_defaults import YANDEX_SEARCH_URL
from balance_fundraising.yandex_api import load_env_file, require_env


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


def build_yandex_search_request(query: str, *, page: int = 0, groups_on_page: int = 10) -> Dict[str, object]:
    return {
        "query": {
            "searchType": "SEARCH_TYPE_RU",
            "queryText": query,
            "familyMode": "FAMILY_MODE_MODERATE",
            "page": page,
            "fixTypoMode": "FIX_TYPO_MODE_ON",
        },
        "sortSpec": {"sortMode": "SORT_MODE_BY_RELEVANCE"},
        "groupSpec": {"groupMode": "GROUP_MODE_DEEP", "groupsOnPage": groups_on_page, "docsInGroup": 1},
        "maxPassages": 3,
        "l10n": "LOCALIZATION_RU",
    }


class YandexSearchClient:
    def __init__(self, *, api_key: str | None = None, folder_id: str | None = None, endpoint: str | None = None) -> None:
        load_env_file()
        self.api_key = api_key or require_env("YANDEX_API_KEY")
        self.folder_id = folder_id or require_env("YANDEX_FOLDER_ID")
        self.endpoint = endpoint or os.getenv("YANDEX_SEARCH_ENDPOINT", YANDEX_SEARCH_URL)

    def search(self, query: str, *, page: int = 0, groups_on_page: int = 10) -> List[SearchResult]:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install requests to call Yandex Search: pip install -r requirements.txt") from exc

        response = requests.post(
            self.endpoint,
            headers={
                "Authorization": f"Api-Key {self.api_key}",
                "x-folder-id": self.folder_id,
            },
            json=build_yandex_search_request(query, page=page, groups_on_page=groups_on_page),
            timeout=60,
        )
        if not response.ok:
            raise RuntimeError(f"Yandex Search error {response.status_code}: {response.text}")
        payload = response.json()
        raw_data = payload.get("rawData", "")
        return parse_yandex_search_raw_data(raw_data)


def parse_yandex_search_raw_data(raw_data: str) -> List[SearchResult]:
    if not raw_data.strip():
        return []
    if raw_data.lstrip().startswith("<"):
        return _parse_xml_results(raw_data)
    return _parse_htmlish_results(raw_data)


def _parse_xml_results(raw_data: str) -> List[SearchResult]:
    root = ET.fromstring(raw_data)
    results: List[SearchResult] = []
    for doc in _iter_by_tag(root, "doc"):
        url = _text(doc, "url")
        if not url:
            continue
        title = _clean(_text(doc, "title")) or url
        passages = [_clean(node_text) for node_text in _texts(doc, "passage")]
        headline = _clean(_text(doc, "headline"))
        snippet = " ".join(part for part in [headline, *passages] if part)
        results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results


def _parse_htmlish_results(raw_data: str) -> List[SearchResult]:
    urls = re.findall(r"https?://[^\s<>'\"]+", raw_data)
    seen = set()
    results = []
    for url in urls:
        normalized = url.rstrip(").,")
        if normalized not in seen:
            seen.add(normalized)
            results.append(SearchResult(title=normalized, url=normalized))
    return results


def _strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_by_tag(root: ET.Element, tag: str):
    for element in root.iter():
        if _strip_namespace(element.tag) == tag:
            yield element


def _text(root: ET.Element, tag: str) -> str:
    values = _texts(root, tag)
    return values[0] if values else ""


def _texts(root: ET.Element, tag: str) -> List[str]:
    return ["".join(element.itertext()) for element in root.iter() if _strip_namespace(element.tag) == tag]


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

