from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.adapters.web import WebApp, add_opportunity, analyze_opportunity


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalJsonStore(Path(tmp) / "web-smoke-store.json")
        store.init_store()
        app = WebApp(store)
        opportunity = add_opportunity(store, "https://example.org/opportunity")
        analyze_opportunity(
            store,
            opportunity.id,
            source_text="Благотворительные фонды НКО могут подать заявку. Нужны устав, отчетность и рекомендации.",
        )
        root_status, root_html = app.render("/")
        detail_status, detail_html = app.render(f"/opportunities/{opportunity.id}")
    assert root_status == 200
    assert detail_status == 200
    assert "Рабочий стол фандрайзинга" in root_html
    assert "Чек-лист" in detail_html
    assert "Черновик" in detail_html
    print("web_render_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
