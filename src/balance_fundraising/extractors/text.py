from __future__ import annotations

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            text = data.strip()
            if text:
                self.parts.append(text)


def extract_text_from_html(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    return normalize_text(" ".join(parser.parts))


def extract_text_from_docx_bytes(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        xml_content = archive.read("word/document.xml")
    root = ET.fromstring(xml_content)
    texts = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "t" and element.text:
            texts.append(element.text)
    return normalize_text(" ".join(texts))


def extract_text_from_pdf_bytes(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return normalize_text(content.decode("utf-8", errors="ignore"))
    reader = PdfReader(io.BytesIO(content))
    return normalize_text(" ".join(page.extract_text() or "" for page in reader.pages))


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

