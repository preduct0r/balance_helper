from __future__ import annotations

from pathlib import Path

WEB_CSS = (Path(__file__).with_name("static") / "operator.css").read_text(encoding="utf-8")
