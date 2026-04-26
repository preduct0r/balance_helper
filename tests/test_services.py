from __future__ import annotations

import tempfile
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.domain import Opportunity
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.draft import build_application_draft


class ServiceTests(unittest.TestCase):
    def test_draft_uses_fund_wiki_and_marks_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = Opportunity.from_url("https://example.org")
            opportunity.name = "Тестовая площадка"
            opportunity.eligibility = ["НКО"]
            opportunity.missing_info = ["Нет дедлайна"]
            draft = build_application_draft(opportunity, store.list_fund_wiki())
            self.assertIn("Помогать людям с психическими расстройствами", draft)
            self.assertIn("[НУЖНО УТОЧНИТЬ]", draft)
            self.assertIn("Нет дедлайна", draft)

    def test_digest_sorts_urgent_and_overdue(self) -> None:
        overdue = Opportunity.from_url("https://old.example")
        overdue.name = "Old"
        overdue.deadline = "2026-04-12"
        overdue.next_action = "Проверить окно"
        soon = Opportunity.from_url("https://soon.example")
        soon.name = "Soon"
        soon.deadline = "2026-05-01"
        soon.next_action = "Готовить"
        digest = build_digest([soon, overdue], today=date(2026, 4, 26))
        self.assertLess(digest.index("Old"), digest.index("Soon"))
        self.assertIn("просрочено", digest)

    def test_checklist_marks_missing_documents(self) -> None:
        opportunity = Opportunity.from_url("https://example.org")
        checklist = build_checklist(opportunity)
        self.assertIn("[НУЖНО УТОЧНИТЬ] Список документов", checklist)


if __name__ == "__main__":
    unittest.main()

