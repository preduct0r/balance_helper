from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.adapters.web import (
    WebApp,
    add_opportunity,
    analyze_opportunity,
    render_dashboard,
    render_fund_wiki,
    render_opportunity_detail,
    render_review_queue,
)
from balance_fundraising.domain import FundWikiEntry, Opportunity


class WebUiTests(unittest.TestCase):
    def test_dashboard_renderer_shows_urgent_and_missing_deadlines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            overdue = Opportunity.from_url("https://old.example")
            overdue.name = "Старый дедлайн"
            overdue.deadline = "2026-04-12"
            overdue.next_action = "Проверить новое окно"
            missing = Opportunity.from_url("https://missing.example")
            missing.name = "Без дедлайна"
            store.upsert_opportunity(overdue)
            store.upsert_opportunity(missing)
            html = render_dashboard(store)
        self.assertIn("Сегодня важно", html)
        self.assertIn("Нужно проверить", html)
        self.assertIn("Черновики с пробелами", html)
        self.assertIn("Старый дедлайн", html)
        self.assertIn("Без дедлайна", html)
        self.assertIn("Дедлайн неизвестен", html)

    def test_opportunity_detail_renderer_includes_review_materials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = Opportunity.from_url("https://example.org")
            opportunity.name = "Тестовая возможность"
            opportunity.eligibility = ["НКО"]
            opportunity.required_documents = ["Устав фонда"]
            opportunity.missing_info = ["Проверить дедлайн"]
            opportunity.source_snippets = ["Нужны устав и отчетность"]
            opportunity.review_state = "needs_clarification"
            store.upsert_opportunity(opportunity)
            html = render_opportunity_detail(store, opportunity.id)
        self.assertIn("Чек-лист", html)
        self.assertIn("Черновик", html)
        self.assertIn("Работа с записью", html)
        self.assertIn("Что нужно подать", html)
        self.assertIn("Что неизвестно", html)
        self.assertIn("Подтверждения", html)
        self.assertIn("Черновик и факты ниже нельзя отправлять вовне", html)
        self.assertIn("Проверить дедлайн", html)
        self.assertIn("Нужны устав и отчетность", html)
        self.assertIn("[НУЖНО УТОЧНИТЬ]", html)
        self.assertIn("Готовность заявки", html)
        self.assertIn("Пробелы в паспорте фонда", html)

    def test_fund_wiki_page_shows_required_keys_and_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            html = render_fund_wiki(store)
        self.assertIn("Паспорт фонда", html)
        self.assertIn("Социальный результат", html)
        self.assertIn("Юридические данные", html)
        self.assertIn("[НУЖНО УТОЧНИТЬ]", html)

    def test_fund_wiki_post_updates_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            status, location = app.post(
                "/fund-wiki",
                {
                    "value_impact": "100 участников получили поддержку",
                    "source_impact": "Отчет фонда",
                    "owner_impact": "Мария",
                    "review_state_impact": "approved",
                },
            )
            entries = {entry.key: entry for entry in store.list_fund_wiki()}
        self.assertEqual(status, 303)
        self.assertEqual(location, "/fund-wiki")
        self.assertEqual(entries["impact"].value, "100 участников получили поддержку")
        self.assertEqual(entries["impact"].source, "Отчет фонда")
        self.assertEqual(entries["impact"].owner, "Мария")

    def test_review_queue_shows_unreviewed_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            pending = Opportunity.from_url("https://pending.example")
            pending.name = "Нужно проверить"
            pending.review_state = "needs_review"
            reviewed = Opportunity.from_url("https://reviewed.example")
            reviewed.name = "Уже проверено"
            reviewed.status = "accepted"
            reviewed.review_state = "reviewed"
            store.upsert_opportunity(pending)
            store.upsert_opportunity(reviewed)
            html = render_review_queue(store)
        self.assertIn("Очередь проверки", html)
        self.assertIn("Нужно проверить", html)
        self.assertNotIn("Уже проверено", html)

    def test_add_link_handler_creates_opportunity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            status, location = app.post("/opportunities", {"url": "https://example.org/new"})
            opportunity_id = location.rsplit("/", 1)[-1]
        self.assertEqual(status, 303)
        self.assertTrue(opportunity_id.startswith("opp_"))

    def test_analyze_handler_updates_opportunity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = add_opportunity(store, "https://example.org/new")
            opportunity.notes = "Не потерять"
            opportunity.checklist_done = ["Старый пункт"]
            store.upsert_opportunity(opportunity)
            app = WebApp(store)
            status, location = app.post(
                f"/opportunities/{opportunity.id}/analyze",
                {"source_text": "НКО и благотворительные фонды могут подать заявку. Нужны устав и отчетность."},
            )
            updated = store.get_opportunity(opportunity.id)
        self.assertEqual(status, 303)
        self.assertEqual(location, f"/opportunities/{opportunity.id}")
        self.assertEqual(updated.status, "needs_review")
        self.assertEqual(updated.review_state, "needs_review")
        self.assertEqual(updated.notes, "Не потерять")
        self.assertIn("Старый пункт", updated.checklist_done)
        self.assertIn("Устав фонда", updated.required_documents)

    def test_operator_actions_update_status_owner_note_and_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = add_opportunity(store, "https://example.org/new")
            app = WebApp(store)
            app.post(
                f"/opportunities/{opportunity.id}/status",
                {"status": "not_started", "review_state": "needs_clarification"},
            )
            app.post(f"/opportunities/{opportunity.id}/owner", {"owner": "Анна"})
            app.post(f"/opportunities/{opportunity.id}/note", {"notes": "Позвонить партнёру"})
            app.post(f"/opportunities/{opportunity.id}/checklist", {"item": "Устав фонда"})
            app.post(f"/opportunities/{opportunity.id}/readiness", {"readiness_state": "preparing_documents"})
            updated = store.get_opportunity(opportunity.id)
        self.assertEqual(updated.status, "not_started")
        self.assertEqual(updated.review_state, "needs_clarification")
        self.assertEqual(updated.owner, "Анна")
        self.assertEqual(updated.notes, "Позвонить партнёру")
        self.assertIn("Устав фонда", updated.checklist_done)
        self.assertEqual(updated.readiness_state, "preparing_documents")

    def test_render_route_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            self.assertEqual(app.render("/")[0], 200)
            self.assertEqual(app.render("/review")[0], 200)
            self.assertEqual(app.render("/fund-wiki")[0], 200)
            status, location = app.post("/opportunities", {"url": "https://example.org/new"})
            opportunity_id = location.rsplit("/", 1)[-1]
            self.assertEqual(status, 303)
            self.assertEqual(app.render(f"/opportunities/{opportunity_id}")[0], 200)
            app.post(f"/opportunities/{opportunity_id}/analyze", {"source_text": "НКО. Нужна отчетность."})
            detail_status, detail_html = app.render(f"/opportunities/{opportunity_id}")
        self.assertEqual(detail_status, 200)
        self.assertIn("Отчетность фонда", detail_html)

    def test_detail_readiness_improves_when_fund_wiki_gaps_are_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            for key in ["impact", "legal_details", "reports", "public_links", "presentation"]:
                store.upsert_fund_wiki_entry(FundWikiEntry(key=key, value=f"{key} value", source="Тест"))
            opportunity = Opportunity.from_url("https://ready.example")
            opportunity.name = "Готовая площадка"
            opportunity.deadline = "2026-06-01"
            opportunity.required_documents = ["Устав фонда"]
            opportunity.checklist_done = ["Устав фонда"]
            opportunity.confidence = 0.9
            store.upsert_opportunity(opportunity)
            html = render_opportunity_detail(store, opportunity.id)
        self.assertIn("Можно готовить к ручной проверке", html)


if __name__ == "__main__":
    unittest.main()
