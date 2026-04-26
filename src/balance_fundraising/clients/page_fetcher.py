from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from balance_fundraising.extractors.text import extract_text_from_docx_bytes, extract_text_from_html, extract_text_from_pdf_bytes


@dataclass
class FetchedDocument:
    url: str
    content_type: str
    text: str


class PageFetcher:
    def fetch(self, url: str) -> FetchedDocument:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install requests to fetch pages: pip install -r requirements.txt") from exc
        response = requests.get(url, timeout=60, headers={"User-Agent": "balance-fundraising/0.1"})
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        text = extract_text_from_bytes(response.content, content_type=content_type, url=url)
        return FetchedDocument(url=url, content_type=content_type, text=text)


def extract_text_from_bytes(content: bytes, *, content_type: str = "", url: str = "") -> str:
    suffix = Path(url).suffix.lower()
    if "html" in content_type or suffix in {"", ".html", ".htm"}:
        return extract_text_from_html(content.decode("utf-8", errors="ignore"))
    if "text" in content_type or suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore")
    if "wordprocessingml" in content_type or suffix == ".docx":
        return extract_text_from_docx_bytes(content)
    if "pdf" in content_type or suffix == ".pdf":
        return extract_text_from_pdf_bytes(content)
    return content.decode("utf-8", errors="ignore")

