from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.domain import ActivityLogEntry, Opportunity
from balance_fundraising.extractors.text import extract_text_from_html
from balance_fundraising.services.analysis import OpportunityAnalysisService
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.draft import build_application_draft


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalJsonStore(Path(tmp) / "operator-smoke-store.json")
        store.init_store()
        opportunity = Opportunity.from_url("https://dobro.mail.ru/funds/registration/")
        store.upsert_opportunity(opportunity)
        store.add_activity(ActivityLogEntry.today(action="add_link", entity_id=opportunity.id, details=opportunity.url))

        fixture_text = extract_text_from_html((ROOT / "tests/fixtures/vk_dobro.html").read_text(encoding="utf-8"))
        analyzed = OpportunityAnalysisService(store).analyze_opportunity(opportunity.id, text=fixture_text)
        checklist = build_checklist(analyzed)
        draft = build_application_draft(analyzed, store.list_fund_wiki())
        digest = build_digest(store.list_opportunities())

    print("Smoke workflow: добавить ссылку -> разобрать -> чек-лист -> черновик -> digest")
    print(f"ID: {analyzed.id}")
    print(f"Название: {analyzed.name}")
    print(f"Статус: {analyzed.status}")
    print("\n--- Чек-лист ---")
    print(checklist)
    print("\n--- Черновик ---")
    print(draft)
    print("\n--- Digest ---")
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

