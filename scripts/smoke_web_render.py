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
from balance_fundraising.domain import FundWikiEntry


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
        root_status, root_html = app.render("/")
        applications_status, applications_html = app.render("/applications")
        application_detail_status, application_detail_html = app.render(f"/applications/{application.id}")
        first_run_status, first_run_html = app.render("/first-run")
        review_status, review_html = app.render("/review")
        wiki_status, wiki_html = app.render("/fund-wiki")
        detail_status, detail_html = app.render(f"/opportunities/{opportunity.id}")
    assert root_status == 200
    assert applications_status == 200
    assert application_detail_status == 200
    assert first_run_status == 200
    assert review_status == 200
    assert wiki_status == 200
    assert detail_status == 200
    assert "Рабочий стол фандрайзинга" in root_html
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
