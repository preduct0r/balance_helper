from __future__ import annotations

import tempfile
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.clients.yandex_search import SearchResult
from balance_fundraising.domain import ActivityLogEntry, Application, FundWikiEntry, FundraisingLead, Opportunity
from balance_fundraising.services.applications import (
    build_reporting_checklist,
    create_application_for_opportunity,
    update_application_reporting,
    update_application_response,
    update_application_status,
    update_feedback_status,
)
from balance_fundraising.services.b2b import (
    B2BDiscoveryService,
    analyze_b2b_lead,
    build_b2b_draft,
    sanitize_b2b_error,
)
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.demo import seed_demo_store
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.discovery import DiscoveryService
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
        self.assertEqual(application.response_summary, "")
        self.assertEqual(application.reporting_state, "not_started")
        self.assertIsNone(application.reporting_done_at)

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

    def test_application_response_and_reporting_are_logged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = Opportunity.from_url("https://example.org/app")
            store.upsert_opportunity(opportunity)
            application = create_application_for_opportunity(store, opportunity.id)
            update_application_response(store, application.id, status="accepted", response_summary="Приняли, нужен отчет")
            update_application_reporting(
                store,
                application.id,
                reporting_state="prepared_by_human",
                reporting_done_at="2026-05-10",
                notes="Отчет проверила Анна",
            )
            stored = store.get_application(application.id)
            activity = store.list_activity()
        self.assertEqual(stored.status, "accepted")
        self.assertEqual(stored.response_summary, "Приняли, нужен отчет")
        self.assertEqual(stored.reporting_state, "prepared_by_human")
        self.assertEqual(stored.reporting_done_at, "2026-05-10")
        self.assertTrue(any(item.action == "application_response" for item in activity))
        self.assertTrue(any(item.action == "application_reporting" for item in activity))

    def test_reporting_checklist_uses_opportunity_requirements_and_missing_markers(self) -> None:
        opportunity = Opportunity.from_url("https://example.org/reporting")
        application = Application(id="app_1", opportunity_id=opportunity.id, status="reporting_needed")
        checklist = build_reporting_checklist(application, opportunity)
        self.assertIn("[НУЖНО УТОЧНИТЬ] Требования к отчету", checklist)
        self.assertIn("[НУЖНО УТОЧНИТЬ] Срок отчета", checklist)
        self.assertIn("[НУЖНО УТОЧНИТЬ] Ответственный", checklist)
        opportunity.reporting_requirements = ["Финансовый отчет", "Содержательный отчет"]
        application.reporting_due_at = "2026-05-20"
        application.owner = "Анна"
        checklist = build_reporting_checklist(application, opportunity)
        self.assertIn("Финансовый отчет", checklist)
        self.assertIn("2026-05-20", checklist)
        self.assertIn("Анна", checklist)

    def test_digest_ignores_prepared_reporting(self) -> None:
        application = Application(
            id="app_report",
            opportunity_id="opp_report",
            status="reporting_needed",
            reporting_due_at="2026-04-12",
            reporting_state="prepared_by_human",
            owner="Анна",
        )
        digest = build_digest([], applications=[application], today=date(2026, 4, 26))
        self.assertEqual(digest, "Срочных действий нет.")

    def test_feedback_status_updates_activity_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            entry = ActivityLogEntry.today(action="operator_feedback", entity_id="first-run", details="Неясно")
            store.add_activity(entry)
            activity_id = store.list_activity()[0].id
            updated = update_feedback_status(store, activity_id, "converted_to_task")
        self.assertEqual(updated.status, "converted_to_task")

    def test_discovery_deduplicates_and_writes_run_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            existing = Opportunity.from_url("https://example.org/existing")
            existing.name = "Старая запись"
            existing.status = "accepted"
            store.upsert_opportunity(existing)
            service = DiscoveryService(store, FakeSearchClient())
            result = service.discover(["тестовый запрос"], limit_per_query=5)
            opportunities = {item.url: item for item in store.list_opportunities()}
            activity = store.list_activity()
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.existing_count, 1)
        self.assertEqual(result.status, "completed")
        self.assertIn("https://example.org/new", opportunities)
        self.assertEqual(opportunities["https://example.org/existing"].status, "accepted")
        self.assertEqual(opportunities["https://example.org/existing"].last_checked, date.today().isoformat())
        self.assertTrue(any(item.action == "discover_run" and "created=1" in item.details for item in activity))

    def test_discovery_failure_logs_sanitized_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"YANDEX_API_KEY": "SECRET_KEY", "YANDEX_FOLDER_ID": "SECRET_FOLDER"},
        ):
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            result = DiscoveryService(store, FailingSearchClient()).discover(["ошибка"], limit_per_query=5)
            activity = store.list_activity()
            details = "\n".join(item.details for item in activity)
        self.assertEqual(result.status, "failed")
        self.assertIn("discover_error", {item.action for item in activity})
        self.assertNotIn("SECRET_KEY", details)
        self.assertNotIn("SECRET_FOLDER", details)

    def test_fundraising_lead_defaults_and_local_store_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            lead = FundraisingLead.from_values(
                category="b2b",
                name="Компания заботы",
                organization="ООО Забота",
                url="https://company.example",
            )
            lead.risk_flags = ["Проверить репутацию"]
            store.upsert_lead(lead)
            updated = store.update_lead_fields(lead.id, {"owner": "Анна", "status": "contact_planned"})
            stored = store.get_lead(lead.id)
        self.assertTrue(lead.id.startswith("lead_"))
        self.assertEqual(stored.category, "b2b")
        self.assertEqual(updated.owner, "Анна")
        self.assertEqual(stored.status, "contact_planned")
        self.assertEqual(stored.risk_flags, ["Проверить репутацию"])

    def test_digest_includes_lead_followups_and_review(self) -> None:
        lead = FundraisingLead.from_values(category="b2b", name="HR partner", url="https://hr.example")
        lead.recheck_at = "2026-04-12"
        lead.deadline = "2026-05-01"
        lead.next_action = "Вернуться с письмом"
        digest = build_digest([], leads=[lead], today=date(2026, 4, 26))
        self.assertIn(lead.id, digest)
        self.assertIn("нет ответственного", digest)
        self.assertIn("проверка просрочена", digest)
        self.assertIn("дедлайн 2026-05-01", digest)

    def test_b2b_radar_creates_b2b_leads_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            existing = FundraisingLead.from_values(
                category="b2b",
                name="Старая компания",
                url="https://company.example/existing",
            )
            existing.status = "accepted"
            store.upsert_lead(existing)
            result = B2BDiscoveryService(store, FakeB2BSearchClient()).discover(["mental health hr"], limit_per_query=5)
            leads = {item.url: item for item in store.list_leads()}
            activity = store.list_activity()
        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.existing_count, 1)
        self.assertEqual(result.status, "completed")
        self.assertEqual(leads["https://company.example/new"].category, "b2b")
        self.assertEqual(leads["https://company.example/new"].status, "needs_review")
        self.assertEqual(leads["https://company.example/existing"].status, "accepted")
        self.assertTrue(any(item.action == "b2b_discover_run" and "created=1" in item.details for item in activity))

    def test_b2b_radar_failure_logs_sanitized_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            "os.environ",
            {"YANDEX_API_KEY": "SECRET_KEY", "YANDEX_FOLDER_ID": "SECRET_FOLDER"},
        ):
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            result = B2BDiscoveryService(store, FailingB2BSearchClient()).discover(["ошибка"], limit_per_query=5)
            activity = store.list_activity()
            details = "\n".join(item.details for item in activity)
        self.assertEqual(result.status, "failed")
        self.assertIn("b2b_discover_error", {item.action for item in activity})
        self.assertNotIn("SECRET_KEY", details)
        self.assertNotIn("SECRET_FOLDER", details)
        self.assertEqual(sanitize_b2b_error("SECRET failure"), "[скрыто] failure")

    def test_b2b_analysis_fills_fit_risks_missing_info_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            lead = FundraisingLead.from_values(category="b2b", name="HR Tech", url="https://hr.example")
            store.upsert_lead(lead)
            analyzed = analyze_b2b_lead(
                store,
                lead.id,
                text="Компания развивает HR wellbeing и корпоративное обучение. Есть форма обратной связи. Риски: репутация требует проверки.",
            )
        self.assertIn("HR wellbeing", analyzed.fit_for_fund)
        self.assertIn("Проверить репутацию", analyzed.risk_flags)
        self.assertIn("Уточнить ответственного за партнерства", analyzed.missing_info)
        self.assertIn("форма обратной связи", analyzed.contact)
        self.assertGreater(analyzed.confidence, 0.5)
        self.assertTrue(analyzed.source_snippets)

    def test_b2b_draft_uses_only_fund_wiki_and_lead_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            lead = FundraisingLead.from_values(category="b2b", name="HR Tech", url="https://hr.example")
            lead.fit_for_fund = "HR wellbeing"
            lead.source_snippets = ["Компания пишет про wellbeing"]
            lead.notes = "Секретная заметка: нельзя использовать"
            store.upsert_lead(lead)
            draft = build_b2b_draft(lead, store.list_fund_wiki())
        self.assertIn("Черновик первого письма", draft)
        self.assertIn("One-pager", draft)
        self.assertIn("Помогать людям с психическими расстройствами", draft)
        self.assertIn("HR wellbeing", draft)
        self.assertIn("Компания пишет про wellbeing", draft)
        self.assertIn("[НУЖНО УТОЧНИТЬ]", draft)
        self.assertNotIn("Секретная заметка", draft)


class FakeSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [
            SearchResult(title="Новая площадка", url="https://example.org/new", snippet="НКО могут подать заявку"),
            SearchResult(title="Старая площадка", url="https://example.org/existing", snippet="Обновленный фрагмент"),
        ]


class FailingSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        raise RuntimeError("Yandex failed with SECRET_KEY in SECRET_FOLDER")


class FakeB2BSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [
            SearchResult(title="Новая компания", url="https://company.example/new", snippet="HR wellbeing для сотрудников"),
            SearchResult(title="Старая компания", url="https://company.example/existing", snippet="Обновленный фрагмент"),
        ]


class FailingB2BSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        raise RuntimeError("Yandex failed with SECRET_KEY in SECRET_FOLDER")


if __name__ == "__main__":
    unittest.main()
