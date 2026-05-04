from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.adapters.web import (
    WebApp,
    add_opportunity,
    analyze_opportunity,
    render_blogger_detail,
    render_bloggers,
    render_b2b,
    render_b2b_detail,
    render_donor_campaign_detail,
    render_donor_campaigns,
    render_application_detail,
    render_applications,
    render_dashboard,
    render_event_detail,
    render_events,
    render_fund_wiki,
    render_lead_detail,
    render_leads,
    render_opportunity_detail,
    render_offer_detail,
    render_offers,
    render_radar,
    render_review_queue,
)
from balance_fundraising.clients.yandex_search import SearchResult
from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, FundraisingLead, Opportunity, ServiceOffer


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

    def test_leads_list_detail_and_safe_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            status, location = app.post(
                "/leads",
                {
                    "category": "b2b",
                    "name": "Компания заботы",
                    "organization": "ООО Забота",
                    "url": "https://company.example",
                    "description": "HR wellbeing",
                },
            )
            lead_id = location.rsplit("/", 1)[-1]
            app.post(f"/leads/{lead_id}/owner", {"owner": "Анна"})
            app.post(f"/leads/{lead_id}/status", {"status": "contact_planned", "review_state": "needs_review"})
            app.post(f"/leads/{lead_id}/note", {"notes": "Подготовить письмо вручную"})
            list_html = render_leads(store)
            detail_html = render_lead_detail(store, lead_id)
            review_html = render_review_queue(store)
            updated = store.get_lead(lead_id)
        self.assertEqual(status, 303)
        self.assertEqual(location, f"/leads/{lead_id}")
        self.assertEqual(updated.owner, "Анна")
        self.assertEqual(updated.status, "contact_planned")
        self.assertEqual(updated.notes, "Подготовить письмо вручную")
        self.assertIn("Контакты и направления", list_html)
        self.assertIn("Компания заботы", list_html)
        self.assertIn("Карточка контакта", detail_html)
        self.assertIn("HR wellbeing", detail_html)
        self.assertIn("ничего не отправляет", detail_html)
        self.assertIn("Компания заботы", review_html)

    def test_b2b_workspace_runs_radar_and_renders_detail_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store, search_client_factory=lambda: FakeRadarSearchClient(), b2b_search_client_factory=lambda: FakeB2BSearchClient())
            with patch.dict("os.environ", {}, clear=True):
                status, html = app.render("/b2b")
            post_status, location = app.post("/b2b/radar/run", {"query": "hr wellbeing", "limit": "5"})
            lead = store.list_leads()[0]
            analyze_status, analyze_location = app.post(
                f"/b2b/{lead.id}/analyze",
                {"source_text": "Компания развивает HR wellbeing и корпоративное обучение. Есть форма обратной связи."},
            )
            b2b_html = render_b2b(store)
            detail_html = render_b2b_detail(store, lead.id)
            updated = store.get_lead(lead.id)
        self.assertEqual(status, 200)
        self.assertIn("B2B", html)
        self.assertIn("Нужны Yandex-настройки", html)
        self.assertEqual(post_status, 303)
        self.assertEqual(location, "/b2b")
        self.assertEqual(analyze_status, 303)
        self.assertEqual(analyze_location, f"/b2b/{lead.id}")
        self.assertEqual(updated.category, "b2b")
        self.assertIn("B2B компания", b2b_html)
        self.assertIn("Черновик первого письма", detail_html)
        self.assertIn("One-pager", detail_html)
        self.assertIn("ничего не отправляет", detail_html)

    def test_offers_workspace_and_b2b_detail_show_approved_offer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            status, location = app.post(
                "/offers",
                {
                    "name": "Корпоративная лекция",
                    "offer_type": "corporate_lecture",
                    "audience": "HR-команды",
                    "format": "Онлайн",
                    "value_proposition": "Психопросвещение для сотрудников",
                },
            )
            offer_id = location.rsplit("/", 1)[-1]
            app.post(
                f"/offers/{offer_id}",
                {
                    "audience": "HR и руководители",
                    "format": "Онлайн 90 минут",
                    "value_proposition": "Психопросвещение для сотрудников",
                    "requirements": "Бриф",
                    "materials_needed": "Презентация",
                    "source_snippets": "Описание проверено командой",
                    "missing_info": "Уточнить цену",
                },
            )
            app.post(f"/offers/{offer_id}/owner", {"owner": "Анна"})
            app.post(f"/offers/{offer_id}/status", {"status": "approved", "review_state": "approved"})
            app.post(f"/offers/{offer_id}/note", {"notes": "Использовать только после ручной проверки"})
            lead = FundraisingLead.from_values(category="b2b", name="HR Tech", url="https://hr.example")
            lead.fit_for_fund = "HR wellbeing"
            lead.source_snippets = ["Компания пишет про wellbeing"]
            store.upsert_lead(lead)
            offers_html = render_offers(store)
            detail_html = render_offer_detail(store, offer_id)
            b2b_html = render_b2b_detail(store, lead.id)
            updated = store.get_service_offer(offer_id)
        self.assertEqual(status, 303)
        self.assertEqual(location, f"/offers/{offer_id}")
        self.assertEqual(updated.owner, "Анна")
        self.assertEqual(updated.status, "approved")
        self.assertEqual(updated.review_state, "approved")
        self.assertIn("Услуги", offers_html)
        self.assertIn("Корпоративная лекция", offers_html)
        self.assertIn("Карточка услуги", detail_html)
        self.assertIn("Уточнить цену", detail_html)
        self.assertIn("ничего не продает", detail_html)
        self.assertIn("Корпоративная лекция", b2b_html)
        self.assertIn("Психопросвещение для сотрудников", b2b_html)

    def test_events_workspace_runs_radar_and_renders_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store, event_search_client_factory=lambda: FakeEventSearchClient())
            with patch.dict("os.environ", {}, clear=True):
                status, html = app.render("/events")
            post_status, location = app.post("/events/radar/run", {"query": "НКО маркет", "limit": "5"})
            lead = store.list_leads()[0]
            app.post(f"/events/{lead.id}/owner", {"owner": "Анна"})
            app.post(f"/events/{lead.id}/status", {"status": "contact_planned", "review_state": "needs_review"})
            app.post(f"/events/{lead.id}/note", {"notes": "Проверить взнос и смены волонтеров"})
            events_html = render_events(store)
            detail_html = render_event_detail(store, lead.id)
            review_html = render_review_queue(store)
            updated = store.get_lead(lead.id)
        self.assertEqual(status, 200)
        self.assertIn("Мероприятия", html)
        self.assertIn("Нужны Yandex-настройки", html)
        self.assertEqual(post_status, 303)
        self.assertEqual(location, "/events")
        self.assertEqual(updated.category, "event")
        self.assertEqual(updated.owner, "Анна")
        self.assertIn("НКО-маркеты", events_html)
        self.assertIn("Новый маркет", events_html)
        self.assertIn("Карточка мероприятия", detail_html)
        self.assertIn("Чек-лист мероприятия", detail_html)
        self.assertIn("Мерч и материалы", detail_html)
        self.assertIn("Пост-отчет", detail_html)
        self.assertIn("ничего не отправляет", detail_html)
        self.assertIn("Новый маркет", review_html)

    def test_bloggers_workspace_runs_radar_analyze_and_renders_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store, blogger_search_client_factory=lambda: FakeBloggerSearchClient())
            with patch.dict("os.environ", {}, clear=True):
                status, html = app.render("/bloggers")
            post_status, location = app.post("/bloggers/radar/run", {"query": "психология блог", "limit": "5"})
            lead = store.list_leads()[0]
            app.post(f"/bloggers/{lead.id}/owner", {"owner": "Анна"})
            app.post(f"/bloggers/{lead.id}/status", {"status": "contact_planned", "review_state": "needs_review"})
            app.post(f"/bloggers/{lead.id}/note", {"notes": "Проверить репутацию вручную"})
            analyze_status, analyze_location = app.post(
                f"/bloggers/{lead.id}/analyze",
                {"source_text": "Автор пишет про психологию, ментальное здоровье и инклюзию. Есть форма обратной связи."},
            )
            bloggers_html = render_bloggers(store)
            detail_html = render_blogger_detail(store, lead.id)
            review_html = render_review_queue(store)
            updated = store.get_lead(lead.id)
        self.assertEqual(status, 200)
        self.assertIn("Блогеры", html)
        self.assertIn("Нужны Yandex-настройки", html)
        self.assertEqual(post_status, 303)
        self.assertEqual(location, "/bloggers")
        self.assertEqual(analyze_status, 303)
        self.assertEqual(analyze_location, f"/bloggers/{lead.id}")
        self.assertEqual(updated.category, "blogger")
        self.assertEqual(updated.owner, "Анна")
        self.assertIn("тематические сообщества", bloggers_html)
        self.assertIn("Новый блог", bloggers_html)
        self.assertIn("Карточка блогера", detail_html)
        self.assertIn("Этический чек-лист", detail_html)
        self.assertIn("Черновик предложения коллаборации", detail_html)
        self.assertIn("ничего не отправляет", detail_html)
        self.assertIn("Новый блог", review_html)

    def test_donor_campaign_workspace_create_update_and_render_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            status, location = app.post(
                "/donors",
                {
                    "name": "Майский impact digest",
                    "campaign_type": "impact_digest",
                    "segment": "регулярные доноры",
                    "goal": "Показать результаты месяца",
                },
            )
            campaign_id = location.rsplit("/", 1)[-1]
            app.post(
                f"/donors/{campaign_id}",
                {
                    "audience_description": "Люди, которые уже поддерживают фонд регулярными платежами",
                    "message_channel": "email-рассылка без персональных данных в сервисе",
                    "key_message": "Спасибо, регулярность помогает планировать помощь",
                    "impact_points": "Проведены группы поддержки\nРаботает равное консультирование",
                    "risk_flags": "Проверить тон без давления",
                    "missing_info": "Уточнить свежие цифры",
                    "source_snippets": "Фонд помогает людям с психическими расстройствами жить устойчивее",
                },
            )
            app.post(f"/donors/{campaign_id}/owner", {"owner": "Анна"})
            app.post(f"/donors/{campaign_id}/status", {"status": "ready_for_review", "review_state": "needs_review"})
            app.post(f"/donors/{campaign_id}/note", {"notes": "Внутренний контекст не для черновика"})
            donors_html = render_donor_campaigns(store)
            detail_html = render_donor_campaign_detail(store, campaign_id)
            updated = store.get_donor_campaign(campaign_id)
        self.assertEqual(status, 303)
        self.assertEqual(location, f"/donors/{campaign_id}")
        self.assertEqual(updated.owner, "Анна")
        self.assertEqual(updated.status, "ready_for_review")
        self.assertIn("Доноры", donors_html)
        self.assertIn("Майский impact digest", donors_html)
        self.assertIn("Карточка донорской кампании", detail_html)
        self.assertIn("Черновик донорской кампании", detail_html)
        self.assertIn("персональные данные", detail_html)
        self.assertIn("ничего не отправляет", detail_html)
        self.assertIn("Уточнить свежие цифры", detail_html)
        self.assertNotIn("Внутренний контекст не для черновика", detail_html.split("Черновик донорской кампании", 1)[-1])

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
            self.assertEqual(app.render("/applications")[0], 200)
            self.assertEqual(app.render("/first-run")[0], 200)
            self.assertEqual(app.render("/radar")[0], 200)
            self.assertEqual(app.render("/leads")[0], 200)
            self.assertEqual(app.render("/b2b")[0], 200)
            self.assertEqual(app.render("/offers")[0], 200)
            self.assertEqual(app.render("/events")[0], 200)
            self.assertEqual(app.render("/bloggers")[0], 200)
            self.assertEqual(app.render("/donors")[0], 200)
            status, location = app.post("/opportunities", {"url": "https://example.org/new"})
            opportunity_id = location.rsplit("/", 1)[-1]
            self.assertEqual(status, 303)
            self.assertEqual(app.render(f"/opportunities/{opportunity_id}")[0], 200)
            lead_status, lead_location = app.post("/leads", {"category": "b2b", "name": "Новый контакт"})
            lead_id = lead_location.rsplit("/", 1)[-1]
            self.assertEqual(lead_status, 303)
            self.assertEqual(app.render(f"/leads/{lead_id}")[0], 200)
            self.assertEqual(app.render(f"/b2b/{lead_id}")[0], 200)
            offer_status, offer_location = app.post("/offers", {"name": "Новая услуга", "offer_type": "educational_product"})
            offer_id = offer_location.rsplit("/", 1)[-1]
            self.assertEqual(offer_status, 303)
            self.assertEqual(app.render(f"/offers/{offer_id}")[0], 200)
            event_status, event_location = app.post("/leads", {"category": "event", "name": "Новый маркет"})
            event_id = event_location.rsplit("/", 1)[-1]
            self.assertEqual(event_status, 303)
            self.assertEqual(app.render(f"/events/{event_id}")[0], 200)
            blogger_status, blogger_location = app.post("/leads", {"category": "blogger", "name": "Новый блог"})
            blogger_id = blogger_location.rsplit("/", 1)[-1]
            self.assertEqual(blogger_status, 303)
            self.assertEqual(app.render(f"/bloggers/{blogger_id}")[0], 200)
            donor_status, donor_location = app.post(
                "/donors",
                {"name": "Новая кампания", "campaign_type": "gratitude", "segment": "регулярные доноры", "goal": "Поблагодарить"},
            )
            donor_id = donor_location.rsplit("/", 1)[-1]
            self.assertEqual(donor_status, 303)
            self.assertEqual(app.render(f"/donors/{donor_id}")[0], 200)
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

    def test_application_pipeline_web_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = add_opportunity(store, "https://example.org/application")
            opportunity.name = "Площадка для заявки"
            store.upsert_opportunity(opportunity)
            app = WebApp(store)
            status, location = app.post(f"/opportunities/{opportunity.id}/application", {})
            application = store.list_applications()[0]
            app.post(
                f"/applications/{application.id}/status",
                {"status": "submitted_by_human", "owner": "Анна", "submitted_by": "Анна"},
            )
            app.post(
                f"/applications/{application.id}/dates",
                {"response_due_at": "2026-06-01", "reporting_due_at": "2026-07-01", "recheck_at": "2026-05-15"},
            )
            app.post(f"/applications/{application.id}/note", {"notes": "Подано человеком через форму"})
            applications_html = render_applications(store)
            detail_html = render_opportunity_detail(store, opportunity.id)
            updated = store.get_application(application.id)
        self.assertEqual(status, 303)
        self.assertEqual(location, f"/opportunities/{opportunity.id}")
        self.assertEqual(updated.status, "submitted_by_human")
        self.assertEqual(updated.owner, "Анна")
        self.assertEqual(updated.response_due_at, "2026-06-01")
        self.assertIn("Заявки", applications_html)
        self.assertIn("Площадка для заявки", applications_html)
        self.assertIn("человек уже подал заявку", detail_html)
        self.assertIn("Система ничего не отправляла", detail_html)

    def test_application_detail_and_followup_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = add_opportunity(store, "https://example.org/followup")
            opportunity.name = "Грант с отчетом"
            opportunity.reporting_requirements = ["Финансовый отчет"]
            store.upsert_opportunity(opportunity)
            app = WebApp(store)
            app.post(f"/opportunities/{opportunity.id}/application", {})
            application = store.list_applications()[0]
            status, html = app.render(f"/applications/{application.id}")
            response_status, response_location = app.post(
                f"/applications/{application.id}/response",
                {"status": "accepted", "response_summary": "Приняли, ждут отчет"},
            )
            reporting_status, reporting_location = app.post(
                f"/applications/{application.id}/reporting",
                {"reporting_state": "prepared_by_human", "reporting_done_at": "2026-05-15", "notes": "Отчет проверен"},
            )
            detail_html = render_application_detail(store, application.id)
            updated = store.get_application(application.id)
        self.assertEqual(status, 200)
        self.assertIn("Карточка заявки", html)
        self.assertIn("Грант с отчетом", html)
        self.assertIn("Система ничего не отправляет", html)
        self.assertEqual(response_status, 303)
        self.assertEqual(response_location, f"/applications/{application.id}")
        self.assertEqual(reporting_status, 303)
        self.assertEqual(reporting_location, f"/applications/{application.id}")
        self.assertEqual(updated.status, "accepted")
        self.assertEqual(updated.response_summary, "Приняли, ждут отчет")
        self.assertEqual(updated.reporting_state, "prepared_by_human")
        self.assertIn("Финансовый отчет", detail_html)
        self.assertIn("История", detail_html)

    def test_applications_list_links_records_and_shows_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = add_opportunity(store, "https://example.org/list")
            opportunity.name = "Площадка со сроками"
            store.upsert_opportunity(opportunity)
            app = WebApp(store)
            app.post(f"/opportunities/{opportunity.id}/application", {})
            application = store.list_applications()[0]
            store.update_application_fields(application.id, {"status": "reporting_needed", "reporting_due_at": "2026-04-12"})
            html = render_applications(store)
        self.assertIn(f"/applications/{application.id}", html)
        self.assertIn("нет ответственного", html)
        self.assertIn("отчет просрочен", html)

    def test_first_run_feedback_is_logged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store)
            status, location = app.post(
                "/first-run/feedback",
                {"feedback": "Непонятно, где смотреть отчетность"},
            )
            activity = store.list_activity()
        self.assertEqual(status, 303)
        self.assertEqual(location, "/first-run")
        self.assertTrue(any(item.action == "operator_feedback" for item in activity))

    def test_first_run_shows_feedback_and_status_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            entry = ActivityLogEntry.today(action="operator_feedback", entity_id="first-run", details="Неясен дедлайн")
            store.add_activity(entry)
            feedback_id = store.list_activity()[0].id
            app = WebApp(store)
            html = app.render("/first-run")[1]
            status, location = app.post(f"/feedback/{feedback_id}/status", {"status": "reviewed"})
            updated = store.list_activity()[0]
        self.assertIn("Журнал наблюдений", html)
        self.assertIn("Неясен дедлайн", html)
        self.assertEqual(status, 303)
        self.assertEqual(location, "/first-run")
        self.assertEqual(updated.status, "reviewed")

    def test_radar_renders_queries_runs_discovery_and_feeds_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store, search_client_factory=lambda: FakeRadarSearchClient())
            with patch.dict("os.environ", {}, clear=True):
                status, html = app.render("/radar")
            post_status, location = app.post("/radar/run", {"query": "мой запрос", "limit": "5"})
            radar_html = render_radar(store)
            review_html = render_review_queue(store)
            opportunities = store.list_opportunities()
        self.assertEqual(status, 200)
        self.assertIn("Радар", html)
        self.assertIn("прием заявок НКО платформа", html)
        self.assertIn("Нужны Yandex-настройки", html)
        self.assertEqual(post_status, 303)
        self.assertEqual(location, "/radar")
        self.assertTrue(any(item.status == "discovered" for item in opportunities))
        self.assertIn("Новая программа", radar_html)
        self.assertIn("Новая программа", review_html)

    def test_radar_failed_run_is_operator_friendly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            app = WebApp(store, search_client_factory=lambda: FailingRadarSearchClient())
            status, location = app.post("/radar/run", {"query": "ошибка", "limit": "5"})
            html = render_radar(store)
        self.assertEqual(status, 303)
        self.assertEqual(location, "/radar")
        self.assertIn("failed", html)
        self.assertNotIn("SECRET", html)


class FakeRadarSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="Новая программа", url="https://radar.example/new", snippet="Прием заявок НКО")]


class FailingRadarSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        raise RuntimeError("SECRET search failure")


class FakeB2BSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="B2B компания", url="https://b2b.example/company", snippet="HR wellbeing для сотрудников")]


class FakeEventSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="Новый маркет", url="https://events.example/market", snippet="НКО-маркеты принимают заявки")]


class FakeBloggerSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="Новый блог", url="https://bloggers.example/psy", snippet="Психология и ментальное здоровье")]


if __name__ == "__main__":
    unittest.main()
