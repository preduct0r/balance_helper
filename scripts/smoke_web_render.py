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
from balance_fundraising.clients.yandex_search import SearchResult
from balance_fundraising.domain import FundWikiEntry


class FakeRadarSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="Радарная находка", url="https://example.org/radar", snippet="НКО могут подать заявку")]


class FakeB2BSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="B2B компания", url="https://example.org/b2b", snippet="HR wellbeing для сотрудников")]


class FakeEventSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="Новый НКО-маркет", url="https://example.org/event", snippet="НКО могут участвовать с мерчом")]


class FakeBloggerSearchClient:
    def search(self, query: str, *, groups_on_page: int = 10):
        return [SearchResult(title="Блог о психологии", url="https://example.org/blogger", snippet="Психология и ментальное здоровье")]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalJsonStore(Path(tmp) / "web-smoke-store.json")
        store.init_store()
        app = WebApp(
            store,
            search_client_factory=lambda: FakeRadarSearchClient(),
            b2b_search_client_factory=lambda: FakeB2BSearchClient(),
            event_search_client_factory=lambda: FakeEventSearchClient(),
            blogger_search_client_factory=lambda: FakeBloggerSearchClient(),
        )
        opportunity = add_opportunity(store, "https://example.org/opportunity")
        analyze_opportunity(
            store,
            opportunity.id,
            source_text="Благотворительные фонды НКО могут подать заявку. Нужны устав, отчетность и рекомендации.",
        )
        app.post(
            f"/opportunities/{opportunity.id}/status",
            {"status": "not_started", "review_state": "needs_clarification"},
        )
        store.upsert_fund_wiki_entry(FundWikiEntry(key="impact", value="100 участников", source="Тест"))
        app.post(f"/opportunities/{opportunity.id}/readiness", {"readiness_state": "preparing_documents"})
        app.post(f"/opportunities/{opportunity.id}/application", {})
        application = store.list_applications()[0]
        app.post(
            f"/applications/{application.id}/status",
            {"status": "submitted_by_human", "owner": "Оператор", "submitted_by": "Анна"},
        )
        app.post(
            f"/applications/{application.id}/dates",
            {"submitted_at": "2026-05-04", "response_due_at": "2026-05-20", "reporting_due_at": "", "recheck_at": ""},
        )
        app.post(f"/applications/{application.id}/note", {"notes": "Подано человеком через внешнюю форму."})
        app.post(
            f"/applications/{application.id}/response",
            {"status": "accepted", "response_summary": "Приняли, нужно подготовить отчет."},
        )
        app.post(
            f"/applications/{application.id}/reporting",
            {"reporting_state": "prepared_by_human", "reporting_done_at": "2026-05-25", "notes": "Отчет проверен человеком."},
        )
        app.post("/first-run/feedback", {"feedback": "Не хватило понятной подсказки по отчетности."})
        feedback_id = [item for item in store.list_activity() if item.action == "operator_feedback"][0].id
        app.post(f"/feedback/{feedback_id}/status", {"status": "reviewed"})
        app.post("/radar/run", {"query": "тестовый радар", "limit": "5"})
        app.post(
            "/leads",
            {
                "category": "b2b",
                "name": "Компания заботы",
                "organization": "ООО Забота",
                "url": "https://company.example",
                "description": "HR wellbeing",
            },
        )
        lead = store.list_leads()[0]
        app.post(f"/leads/{lead.id}/owner", {"owner": "Оператор"})
        app.post(f"/leads/{lead.id}/status", {"status": "contact_planned", "review_state": "needs_review"})
        app.post(f"/leads/{lead.id}/note", {"notes": "Подготовить письмо вручную."})
        app.post("/b2b/radar/run", {"query": "hr wellbeing", "limit": "5"})
        b2b_lead = [item for item in store.list_leads() if item.url == "https://example.org/b2b"][0]
        app.post(
            f"/b2b/{b2b_lead.id}/analyze",
            {"source_text": "Компания развивает HR wellbeing и корпоративное обучение. Есть форма обратной связи."},
        )
        offer_status, offer_location = app.post(
            "/offers",
            {
                "name": "Корпоративная лекция",
                "offer_type": "corporate_lecture",
                "audience": "HR-команды",
                "format": "Онлайн 90 минут",
                "value_proposition": "Психопросвещение для сотрудников",
            },
        )
        offer_id = offer_location.rsplit("/", 1)[-1]
        app.post(f"/offers/{offer_id}/status", {"status": "approved", "review_state": "approved"})
        app.post("/events/radar/run", {"query": "НКО маркет", "limit": "5"})
        event_lead = [item for item in store.list_leads() if item.url == "https://example.org/event"][0]
        app.post(f"/events/{event_lead.id}/owner", {"owner": "Оператор"})
        app.post(f"/events/{event_lead.id}/note", {"notes": "Проверить взнос и логистику."})
        app.post("/bloggers/radar/run", {"query": "психология блог", "limit": "5"})
        blogger_lead = [item for item in store.list_leads() if item.url == "https://example.org/blogger"][0]
        app.post(
            f"/bloggers/{blogger_lead.id}/analyze",
            {"source_text": "Автор пишет про психологию, ментальное здоровье и инклюзию. Есть форма обратной связи."},
        )
        app.post(f"/bloggers/{blogger_lead.id}/owner", {"owner": "Оператор"})
        root_status, root_html = app.render("/")
        radar_status, radar_html = app.render("/radar")
        b2b_status, b2b_html = app.render("/b2b")
        b2b_detail_status, b2b_detail_html = app.render(f"/b2b/{b2b_lead.id}")
        offers_status, offers_html = app.render("/offers")
        offer_detail_status, offer_detail_html = app.render(f"/offers/{offer_id}")
        events_status, events_html = app.render("/events")
        event_detail_status, event_detail_html = app.render(f"/events/{event_lead.id}")
        bloggers_status, bloggers_html = app.render("/bloggers")
        blogger_detail_status, blogger_detail_html = app.render(f"/bloggers/{blogger_lead.id}")
        leads_status, leads_html = app.render("/leads")
        lead_detail_status, lead_detail_html = app.render(f"/leads/{lead.id}")
        applications_status, applications_html = app.render("/applications")
        application_detail_status, application_detail_html = app.render(f"/applications/{application.id}")
        first_run_status, first_run_html = app.render("/first-run")
        review_status, review_html = app.render("/review")
        wiki_status, wiki_html = app.render("/fund-wiki")
        detail_status, detail_html = app.render(f"/opportunities/{opportunity.id}")
    assert root_status == 200
    assert radar_status == 200
    assert b2b_status == 200
    assert b2b_detail_status == 200
    assert offer_status == 303
    assert offers_status == 200
    assert offer_detail_status == 200
    assert events_status == 200
    assert event_detail_status == 200
    assert bloggers_status == 200
    assert blogger_detail_status == 200
    assert leads_status == 200
    assert lead_detail_status == 200
    assert applications_status == 200
    assert application_detail_status == 200
    assert first_run_status == 200
    assert review_status == 200
    assert wiki_status == 200
    assert detail_status == 200
    assert "Рабочий стол фандрайзинга" in root_html
    assert "Радар" in radar_html
    assert "Радарная находка" in radar_html
    assert "B2B" in b2b_html
    assert "B2B компания" in b2b_detail_html
    assert "Черновик первого письма" in b2b_detail_html
    assert "Корпоративная лекция" in b2b_detail_html
    assert "Услуги" in offers_html
    assert "Корпоративная лекция" in offer_detail_html
    assert "Мероприятия" in events_html
    assert "Новый НКО-маркет" in event_detail_html
    assert "Чек-лист мероприятия" in event_detail_html
    assert "Мерч и материалы" in event_detail_html
    assert "Блогеры" in bloggers_html
    assert "Блог о психологии" in blogger_detail_html
    assert "Этический чек-лист" in blogger_detail_html
    assert "Черновик предложения коллаборации" in blogger_detail_html
    assert "Контакты и направления" in leads_html
    assert "Компания заботы" in lead_detail_html
    assert "ничего не отправляет" in lead_detail_html
    assert "Заявки" in applications_html
    assert "Карточка заявки" in application_detail_html
    assert "Приняли, нужно подготовить отчет" in application_detail_html
    assert "Отчет подготовлен человеком" in application_detail_html
    assert "Первый прогон" in first_run_html
    assert "Журнал наблюдений" in first_run_html
    assert "Очередь проверки" in review_html
    assert "Паспорт фонда" in wiki_html
    assert "Заявка" in detail_html
    assert "Человек уже подал заявку" in detail_html
    assert "Чек-лист" in detail_html
    assert "Черновик" in detail_html
    assert "Нужно уточнить" in detail_html
    assert "Готовность заявки" in detail_html
    assert "Готовим документы" in detail_html
    print("web_render_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
