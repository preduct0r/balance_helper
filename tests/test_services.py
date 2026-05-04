from __future__ import annotations

import tempfile
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.domain import Application, FundWikiEntry, Opportunity
from balance_fundraising.services.applications import create_application_for_opportunity, update_application_status
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.demo import seed_demo_store
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.draft import build_application_draft
from balance_fundraising.services.readiness import build_readiness


class ServiceTests(unittest.TestCase):
    def test_draft_uses_fund_wiki_and_marks_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = Opportunity.from_url("https://example.org")
            opportunity.name = "Тестовая площадка"
            opportunity.eligibility = ["НКО"]
            opportunity.missing_info = ["Нет дедлайна"]
            opportunity.notes = "Юридические данные: нельзя брать из заметок"
            draft = build_application_draft(opportunity, store.list_fund_wiki())
            self.assertIn("Помогать людям с психическими расстройствами", draft)
            self.assertIn("[НУЖНО УТОЧНИТЬ]", draft)
            self.assertIn("Нет дедлайна", draft)
            self.assertNotIn("нельзя брать из заметок", draft)

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

    def test_opportunity_from_dict_preserves_defaults_for_new_fields(self) -> None:
        opportunity = Opportunity.from_dict({"id": "opp_1", "url": "https://example.org"})
        self.assertEqual(opportunity.notes, "")
        self.assertEqual(opportunity.checklist_done, [])
        self.assertEqual(opportunity.review_state, "needs_review")

    def test_opportunity_from_dict_coerces_new_list_fields(self) -> None:
        opportunity = Opportunity.from_dict(
            {
                "id": "opp_1",
                "url": "https://example.org",
                "checklist_done": "Устав фонда\nОтчетность фонда",
            }
        )
        self.assertEqual(opportunity.checklist_done, ["Устав фонда", "Отчетность фонда"])

    def test_fund_wiki_entry_from_dict_preserves_defaults(self) -> None:
        entry = FundWikiEntry.from_dict({"key": "mission", "value": "Миссия"})
        self.assertEqual(entry.source, "FundWiki")
        self.assertEqual(entry.owner, "")
        self.assertEqual(entry.review_state, "approved")

    def test_readiness_marks_missing_deadline_wiki_and_low_confidence(self) -> None:
        opportunity = Opportunity.from_url("https://example.org")
        opportunity.name = "Тестовая площадка"
        opportunity.required_documents = ["Устав фонда"]
        opportunity.missing_info = ["Проверить контакт"]
        opportunity.confidence = 0.2
        readiness = build_readiness(opportunity, [FundWikiEntry(key="mission", value="Миссия")])
        self.assertFalse(readiness.ready)
        self.assertIn("Уточнить дедлайн", readiness.blockers)
        self.assertIn("Проверить контакт", readiness.blockers)
        self.assertIn("Подтвердить факт: Кому помогает фонд", readiness.blockers)
        self.assertIn("Проверить низкую уверенность разбора", readiness.blockers)

    def test_seed_demo_creates_training_opportunities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            created = seed_demo_store(store)
            opportunities = store.list_opportunities()
        self.assertGreaterEqual(created, 5)
        self.assertGreaterEqual(len(opportunities), 5)
        self.assertTrue(any("VK Добро" in item.name for item in opportunities))
        self.assertTrue(any(item.deadline == "2026-04-12" for item in opportunities))

    def test_application_from_dict_preserves_pipeline_defaults(self) -> None:
        application = Application.from_dict({"id": "app_1", "opportunity_id": "opp_1"})
        self.assertEqual(application.status, "preparing")
        self.assertEqual(application.owner, "")
        self.assertEqual(application.next_action, "Подготовить заявку")

    def test_application_created_from_opportunity_and_status_logged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = Opportunity.from_url("https://example.org/app")
            opportunity.name = "Тестовая заявка"
            store.upsert_opportunity(opportunity)
            application = create_application_for_opportunity(store, opportunity.id)
            updated = update_application_status(store, application.id, "submitted_by_human")
            stored = store.get_application(application.id)
        self.assertEqual(application.opportunity_id, opportunity.id)
        self.assertEqual(stored.status, "submitted_by_human")
        self.assertEqual(updated.next_action, "Ждать ответ или зафиксировать срок ответа")

    def test_digest_includes_application_deadlines_and_missing_owner(self) -> None:
        opportunity = Opportunity.from_url("https://example.org/app")
        opportunity.name = "Площадка"
        application = Application(
            id="app_1",
            opportunity_id=opportunity.id,
            status="waiting_response",
            response_due_at="2026-04-12",
        )
        report = Application(
            id="app_2",
            opportunity_id="opp_report",
            status="reporting_needed",
            reporting_due_at="2026-05-05",
            owner="Анна",
        )
        digest = build_digest([opportunity], applications=[application, report], today=date(2026, 4, 26))
        self.assertIn("app_1", digest)
        self.assertIn("ответ просрочен", digest)
        self.assertIn("нет ответственного", digest)
        self.assertIn("отчет до 2026-05-05", digest)


if __name__ == "__main__":
    unittest.main()
