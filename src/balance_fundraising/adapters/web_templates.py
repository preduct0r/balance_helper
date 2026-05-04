from __future__ import annotations

from datetime import date
from html import escape
from typing import Iterable, List

from balance_fundraising.adapters.web_static import WEB_CSS
from balance_fundraising.domain import ActivityLogEntry, Application, DonorCampaign, FundWikiEntry, FundraisingLead, Opportunity, ServiceOffer
from balance_fundraising.services.applications import (
    APPLICATION_STATUS_LABELS,
    REPORTING_STATE_LABELS,
    application_status_label,
    reporting_state_label,
)
from balance_fundraising.services.fund_wiki import REQUIRED_FUND_WIKI_FIELDS, fund_wiki_by_key, fund_wiki_label
from balance_fundraising.services.leads import LEAD_CATEGORIES, LEAD_STATUSES, lead_category_label, lead_status_label
from balance_fundraising.services.offers import OFFER_STATUSES, OFFER_TYPES, build_offer_description, offer_status_label, offer_type_label
from balance_fundraising.services.donors import (
    DONOR_CAMPAIGN_STATUSES,
    DONOR_CAMPAIGN_TYPES,
    donor_campaign_status_label,
    donor_campaign_type_label,
)
from balance_fundraising.services.readiness import ReadinessReport

STATUS_LABELS = {
    "needs_review": "Нужна проверка",
    "discovered": "Новая находка",
    "not_started": "Не начато",
    "accepted": "Принято",
    "rejected": "Отклонено",
}

REVIEW_STATE_LABELS = {
    "needs_review": "Нужно проверить",
    "needs_clarification": "Нужно уточнить",
    "ready_for_human": "Готово к ручной проверке",
    "reviewed": "Проверено человеком",
    "approved": "Проверено",
}

READINESS_STATE_LABELS = {
    "not_started": "Не начато",
    "preparing_documents": "Готовим документы",
    "ready_for_human": "Готово к ручной проверке",
    "needs_clarification": "Нужно уточнить",
    "postponed": "Отложить",
}


def render_layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>{WEB_CSS}</style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <nav><a href="/">Рабочий стол</a><a href="/radar">Радар</a><a href="/b2b">B2B</a><a href="/offers">Услуги</a><a href="/events">Мероприятия</a><a href="/bloggers">Блогеры</a><a href="/donors">Доноры</a><a href="/opportunities">Возможности</a><a href="/applications">Заявки</a><a href="/leads">Контакты и направления</a><a href="/review">Проверка</a><a href="/fund-wiki">Паспорт фонда</a><a href="/first-run">Первый прогон</a></nav>
  </header>
  <main>{body}</main>
</body>
</html>"""


def render_message(title: str, message: str) -> str:
    return render_layout(title, f"<section><h2>{escape(title)}</h2><p>{escape(message)}</p></section>")


def render_not_found() -> str:
    return render_message("Не найдено", "Такой страницы или записи нет.")


def render_dashboard_page(
    *,
    needs_review: Iterable[Opportunity],
    missing_deadlines: Iterable[Opportunity],
    drafts_with_gaps: Iterable[Opportunity],
    digest_text: str,
) -> str:
    needs_review_rows = list(needs_review)
    missing_deadline_rows = list(missing_deadlines)
    drafts_with_gap_rows = list(drafts_with_gaps)
    body = [
        "<div class=\"grid\">",
        summary_card("Нужно проверить", len(needs_review_rows), "Новые находки и разборы после ИИ"),
        summary_card("Дедлайн неизвестен", len(missing_deadline_rows), "Записи, где нужно уточнить срок"),
        summary_card("Черновики с пробелами", len(drafts_with_gap_rows), "Тексты требуют ручной доработки"),
        "</div>",
        "<section>",
        "<h2>Сегодня важно</h2>",
        f"<pre>{escape(digest_text)}</pre>",
        "</section>",
        "<section>",
        "<h2>Нужно проверить</h2>",
        render_opportunity_table(needs_review_rows, empty_text="Очередь проверки пуста."),
        "</section>",
        "<section>",
        "<h2>Дедлайн неизвестен</h2>",
        render_opportunity_table(missing_deadline_rows, empty_text="Все дедлайны заполнены."),
        "</section>",
        render_add_link_form(),
    ]
    return render_layout("Рабочий стол фандрайзинга", "\n".join(body))


def render_opportunity_list_page(opportunities: Iterable[Opportunity]) -> str:
    body = [
        "<section>",
        "<h2>Все возможности</h2>",
        render_opportunity_table(opportunities, empty_text="Пока нет возможностей."),
        "</section>",
        render_add_link_form(),
    ]
    return render_layout("Возможности", "\n".join(body))


def render_lead_list_page(leads: Iterable[FundraisingLead]) -> str:
    body = [
        "<section>",
        "<h2>Контакты и направления</h2>",
        "<p class=\"muted\">Общее рабочее место для будущих направлений: бизнес, платные услуги, мероприятия, блогеры и донорские кампании.</p>",
        render_lead_table(leads, empty_text="Пока нет контактов и направлений."),
        "</section>",
        render_add_lead_form(),
    ]
    return render_layout("Контакты и направления", "\n".join(body))


def render_service_offer_list_page(offers: Iterable[ServiceOffer]) -> str:
    body = [
        "<section>",
        "<h2>Услуги фонда</h2>",
        "<p class=\"muted\">Внутренний список платных услуг и образовательных форматов. Система ничего не продает и не отправляет наружу.</p>",
        render_service_offer_table(offers, empty_text="Пока нет платных услуг."),
        "</section>",
        render_add_service_offer_form(),
    ]
    return render_layout("Услуги", "\n".join(body))


def render_donor_campaign_list_page(campaigns: Iterable[DonorCampaign]) -> str:
    body = [
        "<section>",
        "<h2>Донорские кампании</h2>",
        "<p class=\"muted\">Бережные сегментные кампании: благодарности, impact digest, реактивация и объяснение регулярных пожертвований. Здесь нет персональных данных доноров, рассылок и внешних отправок.</p>",
        render_donor_campaign_table(campaigns, empty_text="Пока нет донорских кампаний."),
        "</section>",
        render_add_donor_campaign_form(),
    ]
    return render_layout("Доноры", "\n".join(body))


def render_b2b_page(
    *,
    queries: Iterable[str],
    activity: Iterable[ActivityLogEntry],
    leads: Iterable[FundraisingLead],
    yandex_configured: bool,
) -> str:
    query_options = "".join(f"<option value=\"{escape(query, quote=True)}\">{escape(query)}</option>" for query in queries)
    warning = (
        ""
        if yandex_configured
        else "<div class=\"callout\">Нужны Yandex-настройки для реального B2B-поиска: YANDEX_API_KEY и YANDEX_FOLDER_ID. Тесты и демо не вызывают внешний поиск.</div>"
    )
    runs = [item for item in activity if item.action in {"b2b_discover_run", "b2b_discover_error"}]
    body = [
        "<section>",
        "<h2>B2B партнёры</h2>",
        "<p class=\"muted\">Поиск компаний и рабочих гипотез партнерства. Система только готовит материалы для ручной проверки.</p>",
        warning,
        "<form method=\"post\" action=\"/b2b/radar/run\">",
        f"<label>Кураторский запрос <select name=\"selected_query\"><option value=\"\">Все запросы</option>{query_options}</select></label>",
        "<label>Свой запрос на один запуск <input name=\"custom_query\" placeholder=\"Например: HR wellbeing НКО партнерство\"></label>",
        "<label>Сколько результатов на запрос <input name=\"limit\" type=\"number\" min=\"1\" max=\"20\" value=\"5\"></label>",
        "<button type=\"submit\">Запустить B2B-поиск</button>",
        "</form>",
        "</section>",
        "<section>",
        "<h2>Последние B2B-запуски</h2>",
        render_activity_log(runs[-10:], empty_text="B2B-запусков пока не было."),
        "</section>",
        "<section>",
        "<h2>B2B leads</h2>",
        render_lead_table(leads, empty_text="Пока нет B2B-контактов."),
        "</section>",
    ]
    return render_layout("B2B", "\n".join(body))


def render_radar_page(
    *,
    queries: Iterable[str],
    activity: Iterable[ActivityLogEntry],
    opportunities: Iterable[Opportunity],
    yandex_configured: bool,
) -> str:
    query_options = "".join(f"<option value=\"{escape(query, quote=True)}\">{escape(query)}</option>" for query in queries)
    warning = (
        ""
        if yandex_configured
        else "<div class=\"callout\">Нужны Yandex-настройки для реального поиска: YANDEX_API_KEY и YANDEX_FOLDER_ID. Тесты и демо не вызывают внешний поиск.</div>"
    )
    runs = [item for item in activity if item.action in {"discover_run", "discover_error"}]
    body = [
        "<section>",
        "<h2>Радар возможностей</h2>",
        "<p class=\"muted\">Запускает кураторский поиск площадок и программ. Новые находки остаются в ручной проверке.</p>",
        warning,
        "<form method=\"post\" action=\"/radar/run\">",
        f"<label>Кураторский запрос <select name=\"selected_query\"><option value=\"\">Все запросы</option>{query_options}</select></label>",
        "<label>Свой запрос на один запуск <input name=\"custom_query\" placeholder=\"Например: грант для НКО психическое здоровье\"></label>",
        "<label>Сколько результатов на запрос <input name=\"limit\" type=\"number\" min=\"1\" max=\"20\" value=\"5\"></label>",
        "<button type=\"submit\">Запустить радар</button>",
        "</form>",
        "</section>",
        "<section>",
        "<h2>Последние запуски</h2>",
        render_activity_log(runs[-10:], empty_text="Запусков радара пока не было."),
        "</section>",
        "<section>",
        "<h2>Новые находки</h2>",
        render_opportunity_table(opportunities, empty_text="Пока нет новых находок."),
        "</section>",
    ]
    return render_layout("Радар", "\n".join(body))


def render_event_page(
    *,
    queries: Iterable[str],
    activity: Iterable[ActivityLogEntry],
    leads: Iterable[FundraisingLead],
    yandex_configured: bool,
) -> str:
    query_options = "".join(f"<option value=\"{escape(query, quote=True)}\">{escape(query)}</option>" for query in queries)
    warning = (
        ""
        if yandex_configured
        else "<div class=\"callout\">Нужны Yandex-настройки для реального поиска мероприятий: YANDEX_API_KEY и YANDEX_FOLDER_ID. Тесты и демо не вызывают внешний поиск.</div>"
    )
    runs = [item for item in activity if item.action in {"event_discover_run", "event_discover_error"}]
    body = [
        "<section>",
        "<h2>Мероприятия и мерч</h2>",
        "<p class=\"muted\">НКО-маркеты, благотворительные ярмарки и городские события. Система только помогает подготовить участие и ничего не отправляет наружу.</p>",
        warning,
        "<form method=\"post\" action=\"/events/radar/run\">",
        f"<label>Кураторский запрос <select name=\"selected_query\"><option value=\"\">Все запросы</option>{query_options}</select></label>",
        "<label>Свой запрос на один запуск <input name=\"custom_query\" placeholder=\"Например: благотворительная ярмарка НКО участие\"></label>",
        "<label>Сколько результатов на запрос <input name=\"limit\" type=\"number\" min=\"1\" max=\"20\" value=\"5\"></label>",
        "<button type=\"submit\">Запустить поиск мероприятий</button>",
        "</form>",
        "</section>",
        "<section>",
        "<h2>Последние event-запуски</h2>",
        render_activity_log(runs[-10:], empty_text="Поисков мероприятий пока не было."),
        "</section>",
        "<section>",
        "<h2>Event leads</h2>",
        render_event_lead_table(leads, empty_text="Пока нет мероприятий."),
        "</section>",
    ]
    return render_layout("Мероприятия", "\n".join(body))


def render_blogger_page(
    *,
    queries: Iterable[str],
    activity: Iterable[ActivityLogEntry],
    leads: Iterable[FundraisingLead],
    yandex_configured: bool,
) -> str:
    query_options = "".join(f"<option value=\"{escape(query, quote=True)}\">{escape(query)}</option>" for query in queries)
    warning = (
        ""
        if yandex_configured
        else "<div class=\"callout\">Нужны Yandex-настройки для реального поиска блогеров: YANDEX_API_KEY и YANDEX_FOLDER_ID. Тесты и демо не вызывают внешний поиск.</div>"
    )
    runs = [item for item in activity if item.action in {"blogger_discover_run", "blogger_discover_error"}]
    body = [
        "<section>",
        "<h2>Блогеры и амбассадоры</h2>",
        "<p class=\"muted\">Публичные блогеры и тематические сообщества для бережных коллабораций. Система только готовит материалы для ручной проверки.</p>",
        warning,
        "<form method=\"post\" action=\"/bloggers/radar/run\">",
        f"<label>Кураторский запрос <select name=\"selected_query\"><option value=\"\">Все запросы</option>{query_options}</select></label>",
        "<label>Свой запрос на один запуск <input name=\"custom_query\" placeholder=\"Например: ментальное здоровье блогер НКО\"></label>",
        "<label>Сколько результатов на запрос <input name=\"limit\" type=\"number\" min=\"1\" max=\"20\" value=\"5\"></label>",
        "<button type=\"submit\">Запустить поиск блогеров</button>",
        "</form>",
        "</section>",
        "<section>",
        "<h2>Последние blogger-запуски</h2>",
        render_activity_log(runs[-10:], empty_text="Поисков блогеров пока не было."),
        "</section>",
        "<section>",
        "<h2>Blogger leads</h2>",
        render_blogger_lead_table(leads, empty_text="Пока нет блогеров или сообществ."),
        "</section>",
    ]
    return render_layout("Блогеры", "\n".join(body))


def render_review_queue_page(opportunities: Iterable[Opportunity], leads: Iterable[FundraisingLead] = ()) -> str:
    body = [
        "<section>",
        "<h2>Очередь проверки</h2>",
        "<p class=\"muted\">Здесь собраны новые находки, результаты разбора и черновики, которые нельзя использовать вовне без человека.</p>",
        render_opportunity_table(opportunities, empty_text="Пока нечего проверять."),
        "<h3>Контакты и направления</h3>",
        render_lead_table(leads, empty_text="Пока нет контактов на проверке."),
        "</section>",
    ]
    return render_layout("Проверка", "\n".join(body))


def render_applications_page(applications: Iterable[Application], opportunities: Iterable[Opportunity]) -> str:
    body = [
        "<section>",
        "<h2>Заявки</h2>",
        "<p class=\"muted\">Здесь фиксируется только внутренняя работа. Система ничего не отправляет наружу.</p>",
        render_application_table(applications, opportunities, empty_text="Пока нет заявок."),
        "</section>",
    ]
    return render_layout("Заявки", "\n".join(body))


def render_first_run_page(activity: Iterable[ActivityLogEntry]) -> str:
    checklist = [
        "Добавить одну реальную ссылку или открыть демо-возможность.",
        "Разобрать страницу и проверить факты рядом с подтверждениями.",
        "Заполнить недостающие блоки в паспорте фонда.",
        "Открыть готовность заявки и назначить ответственных за пробелы.",
        "Создать заявку и довести ее до ручной проверки.",
        "Записать наблюдения: что непонятно, чего не хватает, что лишнее.",
    ]
    body = [
        "<section>",
        "<h2>Первый прогон</h2>",
        "<p class=\"muted\">Этот сценарий помогает проверить сервис с оператором без внешних отправок.</p>",
        render_list(checklist, empty_text="Сценарий пока не задан."),
        "<form method=\"post\" action=\"/first-run/feedback\">",
        "<label>Наблюдения оператора<textarea name=\"feedback\" rows=\"5\" placeholder=\"Что было непонятно, чего не хватило, что оказалось лишним\"></textarea></label>",
        "<button type=\"submit\">Сохранить наблюдение</button>",
        "</form>",
        "</section>",
        render_feedback_log(activity),
    ]
    return render_layout("Первый прогон", "\n".join(body))


def render_application_detail_page(
    *,
    application: Application,
    opportunity: Opportunity,
    reporting_checklist: str,
    activity: Iterable[ActivityLogEntry],
) -> str:
    body = [
        "<section>",
        "<h2>Карточка заявки</h2>",
        "<div class=\"callout\">Система ничего не отправляет наружу. Здесь фиксируются только действия человека и следующие шаги.</div>",
        fact_row_html("Возможность", f"<a href=\"/opportunities/{escape(opportunity.id)}\">{escape(opportunity.name)}</a>"),
        fact_row("Стадия", application_status_label(application.status)),
        fact_row("Ответственный", application.owner or "Не назначен"),
        fact_row("Следующий шаг", application.next_action),
        fact_row("Дата подачи", application.submitted_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Срок ответа", application.response_due_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Срок отчета", application.reporting_due_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Проверить позже", application.recheck_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Результат ответа", application.response_summary or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Отчетность", reporting_state_label(application.reporting_state)),
        fact_row("Отчет подготовлен", application.reporting_done_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Заметка", application.notes or "Нет заметки"),
        "</section>",
        render_application_status_form(application, target=f"/applications/{escape(application.id)}/status"),
        render_application_dates_form(application, target=f"/applications/{escape(application.id)}/dates"),
        "<section>",
        "<h2>Ответ площадки</h2>",
        f"<form method=\"post\" action=\"/applications/{escape(application.id)}/response\">",
        f"<label>Результат <select name=\"status\">{application_status_options(application.status)}</select></label>",
        f"<label>Кратко что ответили<textarea name=\"response_summary\" rows=\"4\">{escape(application.response_summary)}</textarea></label>",
        "<button type=\"submit\">Зафиксировать ответ</button>",
        "</form>",
        "</section>",
        "<section>",
        "<h2>Отчетность</h2>",
        f"<pre>{escape(reporting_checklist)}</pre>",
        f"<form method=\"post\" action=\"/applications/{escape(application.id)}/reporting\">",
        f"<label>Состояние отчета <select name=\"reporting_state\">{reporting_state_options(application.reporting_state)}</select></label>",
        f"<label>Когда отчет подготовлен человеком <input name=\"reporting_done_at\" value=\"{escape(application.reporting_done_at or '', quote=True)}\" placeholder=\"YYYY-MM-DD\"></label>",
        f"<label>Заметка по отчету<textarea name=\"notes\" rows=\"4\">{escape(application.notes)}</textarea></label>",
        "<button type=\"submit\">Сохранить отчетность</button>",
        "</form>",
        "</section>",
        render_application_note_form(application, target=f"/applications/{escape(application.id)}/note"),
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История заявки пока пуста."),
        "</section>",
    ]
    return render_layout("Карточка заявки", "\n".join(body))


def render_lead_detail_page(lead: FundraisingLead, activity: Iterable[ActivityLogEntry]) -> str:
    body = [
        "<section>",
        "<h2>Карточка контакта</h2>",
        "<div class=\"callout\">Система ничего не отправляет наружу. Здесь только подготовка, проверка и история ручной работы.</div>",
        f"<p>{status_badge(lead_status_label(lead.status))} {review_badge(lead.review_state)}</p>",
        fact_row("Направление", lead_category_label(lead.category)),
        fact_row("Название", lead.name),
        fact_row("Организация", lead.organization),
        fact_row_html("Источник", link(lead.url) if lead.url else "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Описание", lead.description or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Контакт", lead.contact or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Почему подходит", lead.fit_for_fund),
        fact_row("Ответственный", lead.owner or "Не назначен"),
        fact_row("Следующее действие", lead.next_action),
        fact_row("Дедлайн", lead.deadline or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Проверить позже", lead.recheck_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Уверенность", f"{lead.confidence:.2f}"),
        fact_row("Заметка", lead.notes or "Нет заметки"),
        "</section>",
        render_lead_actions(lead),
        "<section><h2>Риски</h2>" + render_list(lead.risk_flags, empty_text="Риски пока не отмечены.") + "</section>",
        "<section><h2>Что неизвестно</h2>" + render_list(lead.missing_info, empty_text="Нет отмеченных пробелов.") + "</section>",
        "<section><h2>Подтверждения</h2>" + render_evidence(lead.source_snippets) + "</section>",
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История контакта пока пуста."),
        "</section>",
    ]
    return render_layout("Карточка контакта", "\n".join(body))


def render_b2b_detail_page(
    lead: FundraisingLead,
    *,
    draft: str,
    activity: Iterable[ActivityLogEntry],
    service_offers: Iterable[ServiceOffer] = (),
) -> str:
    body = [
        "<section>",
        "<h2>B2B карточка</h2>",
        "<div class=\"callout\">Система ничего не отправляет наружу. Черновик ниже нужен только для ручной проверки.</div>",
        f"<p>{status_badge(lead_status_label(lead.status))} {review_badge(lead.review_state)}</p>",
        fact_row("Компания", lead.name),
        fact_row("Организация", lead.organization),
        fact_row_html("Источник", link(lead.url) if lead.url else "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Почему подходит", lead.fit_for_fund),
        fact_row("Контакт", lead.contact or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ответственный", lead.owner or "Не назначен"),
        fact_row("Следующий шаг", lead.next_action),
        fact_row("Уверенность", f"{lead.confidence:.2f}"),
        "</section>",
        render_lead_actions(lead),
        "<section><h2>Риски</h2>" + render_list(lead.risk_flags, empty_text="Риски пока не отмечены.") + "</section>",
        "<section><h2>Что неизвестно</h2>" + render_list(lead.missing_info, empty_text="Нет отмеченных пробелов.") + "</section>",
        "<section><h2>Подтверждения</h2>" + render_evidence(lead.source_snippets) + "</section>",
        "<section><h2>Варианты услуг</h2>" + render_service_offer_list(service_offers) + "</section>",
        render_b2b_analyze_form(lead.id),
        "<section>",
        "<h2>Черновик и one-pager</h2>",
        f"<pre>{escape(draft)}</pre>",
        "</section>",
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История B2B-контакта пока пуста."),
        "</section>",
    ]
    return render_layout("B2B карточка", "\n".join(body))


def render_event_detail_page(
    *,
    lead: FundraisingLead,
    checklist: str,
    activity: Iterable[ActivityLogEntry],
) -> str:
    body = [
        "<section>",
        "<h2>Карточка мероприятия</h2>",
        "<div class=\"callout\">Система ничего не отправляет наружу. Заявки, письма организаторам, публикации и материалы проверяет человек.</div>",
        f"<p>{status_badge(lead_status_label(lead.status))} {review_badge(lead.review_state)}</p>",
        fact_row("Название", lead.name),
        fact_row("Организация", lead.organization),
        fact_row_html("Источник", link(lead.url) if lead.url else "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Описание", lead.description or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Дедлайн", lead.deadline or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ответственный", lead.owner or "Не назначен"),
        fact_row("Следующий шаг", lead.next_action),
        fact_row("Проверить позже", lead.recheck_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Уверенность", f"{lead.confidence:.2f}"),
        fact_row("Заметка", lead.notes or "Нет заметки"),
        "</section>",
        render_lead_actions(lead, target_base="/events"),
        "<section><h2>Риски</h2>" + render_list(lead.risk_flags, empty_text="Риски пока не отмечены.") + "</section>",
        "<section><h2>Что неизвестно</h2>" + render_list(lead.missing_info, empty_text="Нет отмеченных пробелов.") + "</section>",
        "<section><h2>Подтверждения</h2>" + render_evidence(lead.source_snippets) + "</section>",
        "<section>",
        "<h2>Чек-лист мероприятия</h2>",
        f"<pre>{escape(checklist)}</pre>",
        "</section>",
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История мероприятия пока пуста."),
        "</section>",
    ]
    return render_layout("Карточка мероприятия", "\n".join(body))


def render_blogger_detail_page(
    *,
    lead: FundraisingLead,
    checklist: str,
    draft: str,
    activity: Iterable[ActivityLogEntry],
) -> str:
    body = [
        "<section>",
        "<h2>Карточка блогера</h2>",
        "<div class=\"callout\">Система ничего не отправляет наружу. Любой контакт, публикацию, личную историю и формулировку проверяет человек.</div>",
        f"<p>{status_badge(lead_status_label(lead.status))} {review_badge(lead.review_state)}</p>",
        fact_row("Название", lead.name),
        fact_row("Организация/сообщество", lead.organization),
        fact_row_html("Источник", link(lead.url) if lead.url else "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Описание", lead.description or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Почему подходит", lead.fit_for_fund),
        fact_row("Публичный контакт", lead.contact or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ответственный", lead.owner or "Не назначен"),
        fact_row("Следующий шаг", lead.next_action),
        fact_row("Проверить позже", lead.recheck_at or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Уверенность", f"{lead.confidence:.2f}"),
        fact_row("Заметка", lead.notes or "Нет заметки"),
        "</section>",
        render_lead_actions(lead, target_base="/bloggers"),
        "<section><h2>Риски</h2>" + render_list(lead.risk_flags, empty_text="Риски пока не отмечены.") + "</section>",
        "<section><h2>Что неизвестно</h2>" + render_list(lead.missing_info, empty_text="Нет отмеченных пробелов.") + "</section>",
        "<section><h2>Подтверждения</h2>" + render_evidence(lead.source_snippets) + "</section>",
        render_blogger_analyze_form(lead.id),
        "<section>",
        "<h2>Этический чек-лист</h2>",
        f"<pre>{escape(checklist)}</pre>",
        "</section>",
        "<section>",
        "<h2>Черновик</h2>",
        f"<pre>{escape(draft)}</pre>",
        "</section>",
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История блогера пока пуста."),
        "</section>",
    ]
    return render_layout("Карточка блогера", "\n".join(body))


def render_service_offer_detail_page(
    *,
    offer: ServiceOffer,
    draft: str,
    activity: Iterable[ActivityLogEntry],
) -> str:
    body = [
        "<section>",
        "<h2>Карточка услуги</h2>",
        "<div class=\"callout\">Система ничего не продает и не обещает результат. Описание ниже нужно только для ручной проверки.</div>",
        f"<p>{status_badge(offer_status_label(offer.status))} {review_badge(offer.review_state)}</p>",
        fact_row("Название", offer.name),
        fact_row("Тип", offer_type_label(offer.offer_type)),
        fact_row("Аудитория", offer.audience or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Формат", offer.format or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ценность", offer.value_proposition or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ответственный", offer.owner or "Не назначен"),
        fact_row("Заметка", offer.notes or "Нет заметки"),
        "</section>",
        render_service_offer_actions(offer),
        "<section><h2>Требования</h2>" + render_list(offer.requirements, empty_text="[НУЖНО УТОЧНИТЬ] Что нужно от компании") + "</section>",
        "<section><h2>Материалы</h2>" + render_list(offer.materials_needed, empty_text="[НУЖНО УТОЧНИТЬ] Материалы для услуги") + "</section>",
        "<section><h2>Что неизвестно</h2>" + render_list(offer.missing_info, empty_text="Нет отмеченных пробелов.") + "</section>",
        "<section><h2>Подтверждения</h2>" + render_evidence(offer.source_snippets) + "</section>",
        "<section><h2>Описание для ручной проверки</h2>" f"<pre>{escape(draft)}</pre>" "</section>",
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История услуги пока пуста."),
        "</section>",
    ]
    return render_layout("Карточка услуги", "\n".join(body))


def render_donor_campaign_detail_page(
    *,
    campaign: DonorCampaign,
    draft: str,
    ready: bool,
    activity: Iterable[ActivityLogEntry],
) -> str:
    readiness_text = "Можно передать на ручную проверку" if ready else "Есть пробелы перед использованием"
    body = [
        "<section>",
        "<h2>Карточка донорской кампании</h2>",
        "<div class=\"callout\">Система ничего не отправляет наружу и не хранит персональные данные доноров. Работайте только с сегментами, фактами фонда и ручной проверкой.</div>",
        f"<p>{status_badge(donor_campaign_status_label(campaign.status))} {review_badge(campaign.review_state)}</p>",
        fact_row("Название", campaign.name),
        fact_row("Тип", donor_campaign_type_label(campaign.campaign_type)),
        fact_row("Сегмент", campaign.segment or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Цель", campaign.goal or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Канал", campaign.message_channel or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ключевая мысль", campaign.key_message or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Ответственный", campaign.owner or "Не назначен"),
        fact_row("Следующее действие", campaign.next_action),
        fact_row("Заметка", campaign.notes or "Нет заметки"),
        f"<p class=\"{'badge-ok' if ready else 'needs-info'}\">{escape(readiness_text)}</p>",
        "</section>",
        render_donor_campaign_actions(campaign),
        "<section><h2>Impact points</h2>" + render_list(campaign.impact_points, empty_text="[НУЖНО УТОЧНИТЬ] Нужны утвержденные impact-факты") + "</section>",
        "<section><h2>Риски и этические ограничения</h2>" + render_list(campaign.risk_flags, empty_text="Риски пока не отмечены.") + "</section>",
        "<section><h2>Что неизвестно</h2>" + render_list(campaign.missing_info, empty_text="Нет отмеченных пробелов.") + "</section>",
        "<section><h2>Подтверждения</h2>" + render_evidence(campaign.source_snippets) + "</section>",
        "<section><h2>Черновик</h2>" f"<pre>{escape(draft)}</pre>" "</section>",
        "<section>",
        "<h2>История</h2>",
        render_activity_log(activity, empty_text="История кампании пока пуста."),
        "</section>",
    ]
    return render_layout("Карточка донорской кампании", "\n".join(body))


def render_fund_wiki_page(entries: Iterable[FundWikiEntry]) -> str:
    by_key = fund_wiki_by_key(entries)
    rows = []
    for field in REQUIRED_FUND_WIKI_FIELDS:
        entry = by_key.get(field.key, FundWikiEntry(key=field.key, value=""))
        value = entry.value or ""
        rows.append(
            "<section>"
            f"<h2>{escape(field.label)}</h2>"
            f"<p class=\"muted\">{escape(field.prompt)}</p>"
            f"<form method=\"post\" action=\"/fund-wiki\">"
            f"<input type=\"hidden\" name=\"key\" value=\"{escape(field.key)}\">"
            f"<label>Утвержденный текст<textarea name=\"value_{escape(field.key)}\" rows=\"4\" placeholder=\"[НУЖНО УТОЧНИТЬ]\">{escape(value)}</textarea></label>"
            f"<label>Источник <input name=\"source_{escape(field.key)}\" value=\"{escape(entry.source, quote=True)}\" placeholder=\"Документ, отчет или ссылка\"></label>"
            f"<label>Ответственный <input name=\"owner_{escape(field.key)}\" value=\"{escape(entry.owner, quote=True)}\" placeholder=\"Имя\"></label>"
            f"<label>Проверка <select name=\"review_state_{escape(field.key)}\">{fund_wiki_review_options(entry.review_state)}</select></label>"
            f"<p class=\"{'needs-info' if not value else 'muted'}\">{escape(value or '[НУЖНО УТОЧНИТЬ] Этот блок нужен для заявок.')}</p>"
            "<button type=\"submit\">Сохранить блок</button>"
            "</form>"
            "</section>"
        )
    return render_layout("Паспорт фонда", "\n".join(rows))


def render_opportunity_detail_page(
    *,
    opportunity: Opportunity,
    applications: List[Application],
    checklist: str,
    draft: str,
    checklist_items: List[str],
    readiness: ReadinessReport,
) -> str:
    body = [
        "<section>",
        f"<h2>{escape(opportunity.name)}</h2>",
        f"<p>{status_badge(opportunity.status)} {review_badge(opportunity.review_state)}</p>",
        "<div class=\"callout\">Черновик и факты ниже нельзя отправлять вовне без ручной проверки.</div>",
        fact_row_html("Источник", link(opportunity.url)),
        fact_row("Дедлайн", opportunity.deadline or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Тип", opportunity.type),
        fact_row("Следующее действие", opportunity.next_action),
        fact_row("Ответственный", opportunity.owner or "Не назначен"),
        fact_row("Уверенность", f"{opportunity.confidence:.2f}"),
        "</section>",
        render_operator_actions(opportunity),
        render_readiness_block(opportunity, readiness),
        render_opportunity_applications(opportunity, applications),
        "<section>",
        "<h2>Что это</h2>",
        render_list(opportunity.eligibility, empty_text="[НУЖНО УТОЧНИТЬ] Требования к участию"),
        "</section>",
        "<section>",
        "<h2>Что нужно подать</h2>",
        render_list(opportunity.required_documents, empty_text="[НУЖНО УТОЧНИТЬ] Список документов"),
        "</section>",
        "<section>",
        "<h2>Что неизвестно</h2>",
        render_list(opportunity.missing_info, empty_text="Нет отмеченных пробелов."),
        "</section>",
        "<section>",
        "<h2>Подтверждения</h2>",
        render_evidence(opportunity.source_snippets),
        "</section>",
        "<section>",
        "<h2>Рабочий чек-лист</h2>",
        render_checklist_items(opportunity, checklist_items),
        "</section>",
        render_analyze_form(opportunity.id),
        "<section>",
        "<h2>Чек-лист</h2>",
        f"<pre>{escape(checklist)}</pre>",
        "</section>",
        "<section>",
        "<h2>Черновик</h2>",
        f"<pre>{escape(draft)}</pre>",
        "</section>",
    ]
    return render_layout("Карточка возможности", "\n".join(body))


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def review_state_label(review_state: str) -> str:
    return REVIEW_STATE_LABELS.get(review_state, review_state)


def status_badge(status: str) -> str:
    return f"<span class=\"badge\">{escape(status_label(status))}</span>"


def review_badge(review_state: str) -> str:
    css_class = "badge-ok" if review_state == "reviewed" else "badge-warn"
    return f"<span class=\"badge {css_class}\">{escape(review_state_label(review_state))}</span>"


def readiness_state_label(readiness_state: str) -> str:
    return READINESS_STATE_LABELS.get(readiness_state, readiness_state)


def summary_card(title: str, value: int, caption: str) -> str:
    return f"<div class=\"summary-card\"><h3>{escape(title)}</h3><strong>{value}</strong><p class=\"muted\">{escape(caption)}</p></div>"


def fact_row(label: str, value: str) -> str:
    return f"<div class=\"fact\"><strong>{escape(label)}</strong><span>{escape(value)}</span></div>"


def fact_row_html(label: str, value: str) -> str:
    return f"<div class=\"fact\"><strong>{escape(label)}</strong><span>{value}</span></div>"


def link(url: str) -> str:
    safe_url = escape(url, quote=True)
    return f"<a href=\"{safe_url}\" target=\"_blank\" rel=\"noreferrer\">{escape(url)}</a>"


def render_list(items: Iterable[str], *, empty_text: str) -> str:
    values = [item for item in items if item]
    if not values:
        return f"<p class=\"needs-info\">{escape(empty_text)}</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in values) + "</ul>"


def render_evidence(items: Iterable[str]) -> str:
    values = [item for item in items if item]
    if not values:
        return "<p class=\"muted\">Пока нет фрагментов источника.</p>"
    return "".join(f"<div class=\"evidence\">{escape(item)}</div>" for item in values)


def render_add_link_form() -> str:
    return (
        "<section>"
        "<h2>Добавить ссылку</h2>"
        "<form method=\"post\" action=\"/opportunities\">"
        "<label>Ссылка на возможность <input name=\"url\" type=\"url\" required placeholder=\"https://example.org\"></label>"
        "<button type=\"submit\">Добавить</button>"
        "</form>"
        "</section>"
    )


def render_add_lead_form() -> str:
    return (
        "<section>"
        "<h2>Добавить контакт или направление</h2>"
        "<form method=\"post\" action=\"/leads\">"
        f"<label>Направление <select name=\"category\">{lead_category_options('b2b')}</select></label>"
        "<label>Название <input name=\"name\" required placeholder=\"Компания, блогер, маркет или кампания\"></label>"
        "<label>Организация <input name=\"organization\" placeholder=\"Юрлицо, бренд или площадка\"></label>"
        "<label>Ссылка <input name=\"url\" type=\"url\" placeholder=\"https://example.org\"></label>"
        "<label>Краткое описание <textarea name=\"description\" rows=\"4\" placeholder=\"Почему это может быть интересно фонду\"></textarea></label>"
        "<button type=\"submit\">Добавить</button>"
        "</form>"
        "</section>"
    )


def render_add_service_offer_form() -> str:
    return (
        "<section>"
        "<h2>Добавить услугу</h2>"
        "<form method=\"post\" action=\"/offers\">"
        "<label>Название <input name=\"name\" required placeholder=\"Например: корпоративная лекция\"></label>"
        f"<label>Тип <select name=\"offer_type\">{offer_type_options('corporate_lecture')}</select></label>"
        "<label>Аудитория <input name=\"audience\" placeholder=\"HR-команды, руководители, начинающие психологи\"></label>"
        "<label>Формат <input name=\"format\" placeholder=\"Онлайн 90 минут, очный workshop\"></label>"
        "<label>Ценность <textarea name=\"value_proposition\" rows=\"4\" placeholder=\"Что получает компания или участник\"></textarea></label>"
        "<button type=\"submit\">Добавить услугу</button>"
        "</form>"
        "</section>"
    )


def render_add_donor_campaign_form() -> str:
    return (
        "<section>"
        "<h2>Добавить донорскую кампанию</h2>"
        "<form method=\"post\" action=\"/donors\">"
        "<label>Название <input name=\"name\" required placeholder=\"Например: майский impact digest\"></label>"
        f"<label>Тип <select name=\"campaign_type\">{donor_campaign_type_options('impact_digest')}</select></label>"
        "<label>Сегмент <input name=\"segment\" required placeholder=\"Например: регулярные доноры, без ФИО и контактов\"></label>"
        "<label>Цель <textarea name=\"goal\" rows=\"3\" placeholder=\"Чего хотим добиться бережной коммуникацией\"></textarea></label>"
        "<button type=\"submit\">Добавить кампанию</button>"
        "</form>"
        "</section>"
    )


def render_opportunity_table(opportunities: Iterable[Opportunity], *, empty_text: str) -> str:
    rows = list(opportunities)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for opportunity in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/opportunities/{escape(opportunity.id)}\">{escape(opportunity.name)}</a></td>"
            f"<td>{status_badge(opportunity.status)}<br>{review_badge(opportunity.review_state)}</td>"
            f"<td>{escape(opportunity.deadline or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(opportunity.owner or 'Не назначен')}</td>"
            f"<td>{escape(opportunity.next_action)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Название</th><th>Состояние</th><th>Дедлайн</th><th>Ответственный</th><th>Следующее действие</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_application_table(
    applications: Iterable[Application],
    opportunities: Iterable[Opportunity],
    *,
    empty_text: str,
) -> str:
    rows = sorted(applications, key=application_sort_key)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    opportunity_names = {item.id: item.name for item in opportunities}
    body_rows = []
    for application in rows:
        opportunity_name = opportunity_names.get(application.opportunity_id, application.opportunity_id)
        blockers = render_application_blockers(application)
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/applications/{escape(application.id)}\">{escape(opportunity_name)}</a><br><span class=\"muted\">{escape(application.id)}</span></td>"
            f"<td>{status_badge(application_status_label(application.status))}</td>"
            f"<td>{escape(application.owner or 'Не назначен')}</td>"
            f"<td>{escape(application.response_due_at or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(application.reporting_due_at or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(application.next_action)}{blockers}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Возможность</th><th>Стадия</th><th>Ответственный</th><th>Ответ</th><th>Отчет</th><th>Следующий шаг</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_lead_table(leads: Iterable[FundraisingLead], *, empty_text: str) -> str:
    rows = list(leads)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for lead in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/leads/{escape(lead.id)}\">{escape(lead.name)}</a><br><span class=\"muted\">{escape(lead.organization)}</span></td>"
            f"<td>{escape(lead_category_label(lead.category))}</td>"
            f"<td>{status_badge(lead_status_label(lead.status))}<br>{review_badge(lead.review_state)}</td>"
            f"<td>{escape(lead.owner or 'Не назначен')}</td>"
            f"<td>{escape(lead.recheck_at or lead.deadline or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(lead.next_action)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Название</th><th>Направление</th><th>Состояние</th><th>Ответственный</th><th>Дата</th><th>Следующее действие</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_event_lead_table(leads: Iterable[FundraisingLead], *, empty_text: str) -> str:
    rows = list(leads)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for lead in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/events/{escape(lead.id)}\">{escape(lead.name)}</a><br><span class=\"muted\">{escape(lead.organization)}</span></td>"
            f"<td>{status_badge(lead_status_label(lead.status))}<br>{review_badge(lead.review_state)}</td>"
            f"<td>{escape(lead.owner or 'Не назначен')}</td>"
            f"<td>{escape(lead.deadline or lead.recheck_at or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(lead.next_action)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Мероприятие</th><th>Состояние</th><th>Ответственный</th><th>Дата</th><th>Следующее действие</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_blogger_lead_table(leads: Iterable[FundraisingLead], *, empty_text: str) -> str:
    rows = list(leads)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for lead in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/bloggers/{escape(lead.id)}\">{escape(lead.name)}</a><br><span class=\"muted\">{escape(lead.organization)}</span></td>"
            f"<td>{status_badge(lead_status_label(lead.status))}<br>{review_badge(lead.review_state)}</td>"
            f"<td>{escape(lead.owner or 'Не назначен')}</td>"
            f"<td>{escape(lead.recheck_at or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(lead.next_action)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Блогер/сообщество</th><th>Состояние</th><th>Ответственный</th><th>Проверить</th><th>Следующее действие</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_service_offer_table(offers: Iterable[ServiceOffer], *, empty_text: str) -> str:
    rows = list(offers)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for offer in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/offers/{escape(offer.id)}\">{escape(offer.name)}</a><br><span class=\"muted\">{escape(offer_type_label(offer.offer_type))}</span></td>"
            f"<td>{status_badge(offer_status_label(offer.status))}<br>{review_badge(offer.review_state)}</td>"
            f"<td>{escape(offer.audience or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(offer.format or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(offer.owner or 'Не назначен')}</td>"
            f"<td>{escape('; '.join(offer.missing_info) if offer.missing_info else 'Проверить описание')}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Услуга</th><th>Состояние</th><th>Аудитория</th><th>Формат</th><th>Ответственный</th><th>Пробелы</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_donor_campaign_table(campaigns: Iterable[DonorCampaign], *, empty_text: str) -> str:
    rows = list(campaigns)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for campaign in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/donors/{escape(campaign.id)}\">{escape(campaign.name)}</a><br><span class=\"muted\">{escape(donor_campaign_type_label(campaign.campaign_type))}</span></td>"
            f"<td>{status_badge(donor_campaign_status_label(campaign.status))}<br>{review_badge(campaign.review_state)}</td>"
            f"<td>{escape(campaign.segment or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(campaign.owner or 'Не назначен')}</td>"
            f"<td>{escape(campaign.message_channel or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape('; '.join(campaign.missing_info) if campaign.missing_info else campaign.next_action)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Кампания</th><th>Состояние</th><th>Сегмент</th><th>Ответственный</th><th>Канал</th><th>Пробелы</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def render_service_offer_list(offers: Iterable[ServiceOffer]) -> str:
    rows = list(offers)
    if not rows:
        return "<p class=\"needs-info\">[НУЖНО УТОЧНИТЬ] Нет проверенных услуг для предложения.</p>"
    return "<ul>" + "".join(
        f"<li><a href=\"/offers/{escape(offer.id)}\">{escape(offer.name)}</a>: {escape(offer.value_proposition or '[НУЖНО УТОЧНИТЬ]')}</li>"
        for offer in rows
    ) + "</ul>"


def render_checklist_items(opportunity: Opportunity, items: Iterable[str]) -> str:
    values = [item for item in items if item]
    if not values:
        return "<p class=\"needs-info\">[НУЖНО УТОЧНИТЬ] Список задач</p>"
    rows = []
    done = set(opportunity.checklist_done)
    for item in values:
        css_class = "check-item done" if item in done else "check-item"
        action = (
            "<span class=\"badge-ok badge\">Готово</span>"
            if item in done
            else (
                f"<form class=\"inline-form\" method=\"post\" action=\"/opportunities/{escape(opportunity.id)}/checklist\">"
                f"<input type=\"hidden\" name=\"item\" value=\"{escape(item, quote=True)}\">"
                "<button type=\"submit\">Отметить готовым</button>"
                "</form>"
            )
        )
        rows.append(f"<div class=\"{css_class}\"><span>{escape(item)}</span>{action}</div>")
    return "".join(rows)


def render_readiness_block(opportunity: Opportunity, readiness: ReadinessReport) -> str:
    message = "Можно готовить к ручной проверке" if readiness.ready else "Есть пробелы перед заявкой"
    blockers = render_list(readiness.blockers, empty_text="Нет блокирующих пробелов.")
    wiki_gaps = render_list(
        [fund_wiki_label(key) for key in readiness.missing_wiki_keys],
        empty_text="Пробелов в паспорте фонда нет.",
    )
    return (
        "<section>"
        "<h2>Готовность заявки</h2>"
        f"<p>{status_badge(readiness_state_label(readiness.state))}</p>"
        f"<p class=\"{'badge-ok' if readiness.ready else 'needs-info'}\">{escape(message)}</p>"
        "<h3>Что мешает подать</h3>"
        f"{blockers}"
        "<h3>Пробелы в паспорте фонда</h3>"
        f"{wiki_gaps}"
        f"<form method=\"post\" action=\"/opportunities/{escape(opportunity.id)}/readiness\">"
        f"<label>Рабочее состояние <select name=\"readiness_state\">{readiness_state_options(opportunity.readiness_state)}</select></label>"
        "<button type=\"submit\">Сохранить готовность</button>"
        "</form>"
        "</section>"
    )


def render_opportunity_applications(opportunity: Opportunity, applications: List[Application]) -> str:
    if not applications:
        return (
            "<section>"
            "<h2>Заявка</h2>"
            "<p class=\"muted\">Заявка еще не создана. Создание только добавит внутреннюю запись.</p>"
            f"<form method=\"post\" action=\"/opportunities/{escape(opportunity.id)}/application\">"
            "<button type=\"submit\">Создать заявку</button>"
            "</form>"
            "</section>"
        )
    blocks = ["<section><h2>Заявка</h2><div class=\"callout\">Система ничего не отправляла наружу. Статус фиксирует только действия человека.</div>"]
    for application in applications:
        submitted_warning = (
            "<p class=\"needs-info\">человек уже подал заявку; проверьте сроки ответа и отчета</p>"
            if application.status == "submitted_by_human"
            else ""
        )
        blocks.extend(
            [
                f"<h3>{escape(application_status_label(application.status))}</h3>",
                submitted_warning,
                fact_row("Ответственный", application.owner or "Не назначен"),
                fact_row("Подал человек", application.submitted_by or "Не указано"),
                fact_row("Дата подачи", application.submitted_at or "[НУЖНО УТОЧНИТЬ]"),
                fact_row("Срок ответа", application.response_due_at or "[НУЖНО УТОЧНИТЬ]"),
                fact_row("Срок отчета", application.reporting_due_at or "[НУЖНО УТОЧНИТЬ]"),
                fact_row("Проверить позже", application.recheck_at or "[НУЖНО УТОЧНИТЬ]"),
                fact_row("Следующий шаг", application.next_action),
                fact_row_html("Полная карточка", f"<a href=\"/applications/{escape(application.id)}\">Открыть заявку</a>"),
                render_application_status_form(application, target=f"/applications/{escape(application.id)}/status"),
                render_application_dates_form(application, target=f"/applications/{escape(application.id)}/dates"),
                render_application_note_form(application, target=f"/applications/{escape(application.id)}/note"),
            ]
        )
    blocks.append("</section>")
    return "".join(blocks)


def render_operator_actions(opportunity: Opportunity) -> str:
    return (
        "<section>"
        "<h2>Работа с записью</h2>"
        "<div class=\"toolbar\">"
        f"<form method=\"post\" action=\"/opportunities/{escape(opportunity.id)}/status\">"
        "<label>Статус"
        f"<select name=\"status\">{status_options(opportunity.status)}</select>"
        "</label>"
        "<label>Проверка"
        f"<select name=\"review_state\">{review_state_options(opportunity.review_state)}</select>"
        "</label>"
        "<button type=\"submit\">Сохранить состояние</button>"
        "</form>"
        f"<form method=\"post\" action=\"/opportunities/{escape(opportunity.id)}/owner\">"
        f"<label>Ответственный <input name=\"owner\" value=\"{escape(opportunity.owner, quote=True)}\" placeholder=\"Имя\"></label>"
        "<button type=\"submit\">Назначить</button>"
        "</form>"
        "</div>"
        f"<form method=\"post\" action=\"/opportunities/{escape(opportunity.id)}/note\">"
        f"<label>Заметка <textarea name=\"notes\" rows=\"4\" placeholder=\"Что важно помнить по этой возможности\">{escape(opportunity.notes)}</textarea></label>"
        "<button type=\"submit\">Сохранить заметку</button>"
        "</form>"
        "</section>"
    )


def render_lead_actions(lead: FundraisingLead, *, target_base: str = "/leads") -> str:
    safe_base = escape(target_base)
    return (
        "<section>"
        "<h2>Работа с контактом</h2>"
        "<div class=\"toolbar\">"
        f"<form method=\"post\" action=\"{safe_base}/{escape(lead.id)}/status\">"
        f"<label>Статус <select name=\"status\">{lead_status_options(lead.status)}</select></label>"
        f"<label>Проверка <select name=\"review_state\">{review_state_options(lead.review_state)}</select></label>"
        "<button type=\"submit\">Сохранить состояние</button>"
        "</form>"
        f"<form method=\"post\" action=\"{safe_base}/{escape(lead.id)}/owner\">"
        f"<label>Ответственный <input name=\"owner\" value=\"{escape(lead.owner, quote=True)}\" placeholder=\"Имя\"></label>"
        "<button type=\"submit\">Назначить</button>"
        "</form>"
        "</div>"
        f"<form method=\"post\" action=\"{safe_base}/{escape(lead.id)}/note\">"
        f"<label>Заметка <textarea name=\"notes\" rows=\"4\" placeholder=\"Что важно помнить перед ручным контактом\">{escape(lead.notes)}</textarea></label>"
        "<button type=\"submit\">Сохранить заметку</button>"
        "</form>"
        "</section>"
    )


def render_service_offer_actions(offer: ServiceOffer) -> str:
    return (
        "<section>"
        "<h2>Работа с услугой</h2>"
        "<form method=\"post\" action=\"/offers/{id}\">"
        "<label>Аудитория <input name=\"audience\" value=\"{audience}\" placeholder=\"Для кого услуга\"></label>"
        "<label>Формат <input name=\"format\" value=\"{format}\" placeholder=\"Онлайн, очно, длительность\"></label>"
        "<label>Ценность <textarea name=\"value_proposition\" rows=\"4\">{value}</textarea></label>"
        "<label>Требования<textarea name=\"requirements\" rows=\"4\" placeholder=\"Каждый пункт с новой строки\">{requirements}</textarea></label>"
        "<label>Материалы<textarea name=\"materials_needed\" rows=\"4\" placeholder=\"Каждый пункт с новой строки\">{materials}</textarea></label>"
        "<label>Подтверждения<textarea name=\"source_snippets\" rows=\"4\" placeholder=\"Фрагменты утвержденных материалов\">{snippets}</textarea></label>"
        "<label>Что неизвестно<textarea name=\"missing_info\" rows=\"4\" placeholder=\"Каждый пункт с новой строки\">{missing}</textarea></label>"
        "<button type=\"submit\">Сохранить описание</button>"
        "</form>"
        "<div class=\"toolbar\">"
        "<form method=\"post\" action=\"/offers/{id}/status\">"
        "<label>Статус <select name=\"status\">{status_options}</select></label>"
        "<label>Проверка <select name=\"review_state\">{review_options}</select></label>"
        "<button type=\"submit\">Сохранить состояние</button>"
        "</form>"
        "<form method=\"post\" action=\"/offers/{id}/owner\">"
        "<label>Ответственный <input name=\"owner\" value=\"{owner}\" placeholder=\"Имя\"></label>"
        "<button type=\"submit\">Назначить</button>"
        "</form>"
        "</div>"
        "<form method=\"post\" action=\"/offers/{id}/note\">"
        "<label>Заметка <textarea name=\"notes\" rows=\"4\" placeholder=\"Внутренний контекст, не для черновиков\">{notes}</textarea></label>"
        "<button type=\"submit\">Сохранить заметку</button>"
        "</form>"
        "</section>"
    ).format(
        id=escape(offer.id),
        audience=escape(offer.audience, quote=True),
        format=escape(offer.format, quote=True),
        value=escape(offer.value_proposition),
        requirements=escape("\n".join(offer.requirements)),
        materials=escape("\n".join(offer.materials_needed)),
        snippets=escape("\n".join(offer.source_snippets)),
        missing=escape("\n".join(offer.missing_info)),
        status_options=offer_status_options(offer.status),
        review_options=offer_review_options(offer.review_state),
        owner=escape(offer.owner, quote=True),
        notes=escape(offer.notes),
    )


def render_donor_campaign_actions(campaign: DonorCampaign) -> str:
    return (
        "<section>"
        "<h2>Работа с кампанией</h2>"
        "<form method=\"post\" action=\"/donors/{id}\">"
        "<label>Описание аудитории<textarea name=\"audience_description\" rows=\"4\" placeholder=\"Описание сегмента без персональных данных\">{audience}</textarea></label>"
        "<label>Канал <input name=\"message_channel\" value=\"{channel}\" placeholder=\"Ручная рассылка, пост, дайджест\"></label>"
        "<label>Ключевая мысль<textarea name=\"key_message\" rows=\"4\">{key_message}</textarea></label>"
        "<label>Impact points<textarea name=\"impact_points\" rows=\"4\" placeholder=\"Каждый факт с новой строки\">{impact}</textarea></label>"
        "<label>Риски<textarea name=\"risk_flags\" rows=\"4\" placeholder=\"Каждый риск с новой строки\">{risks}</textarea></label>"
        "<label>Что неизвестно<textarea name=\"missing_info\" rows=\"4\" placeholder=\"Каждый пробел с новой строки\">{missing}</textarea></label>"
        "<label>Подтверждения<textarea name=\"source_snippets\" rows=\"4\" placeholder=\"Фрагменты утвержденных материалов\">{snippets}</textarea></label>"
        "<button type=\"submit\">Сохранить описание</button>"
        "</form>"
        "<div class=\"toolbar\">"
        "<form method=\"post\" action=\"/donors/{id}/status\">"
        "<label>Статус <select name=\"status\">{status_options}</select></label>"
        "<label>Проверка <select name=\"review_state\">{review_options}</select></label>"
        "<button type=\"submit\">Сохранить состояние</button>"
        "</form>"
        "<form method=\"post\" action=\"/donors/{id}/owner\">"
        "<label>Ответственный <input name=\"owner\" value=\"{owner}\" placeholder=\"Имя\"></label>"
        "<button type=\"submit\">Назначить</button>"
        "</form>"
        "</div>"
        "<form method=\"post\" action=\"/donors/{id}/note\">"
        "<label>Заметка <textarea name=\"notes\" rows=\"4\" placeholder=\"Внутренний контекст, не для черновиков\">{notes}</textarea></label>"
        "<button type=\"submit\">Сохранить заметку</button>"
        "</form>"
        "</section>"
    ).format(
        id=escape(campaign.id),
        audience=escape(campaign.audience_description),
        channel=escape(campaign.message_channel, quote=True),
        key_message=escape(campaign.key_message),
        impact=escape("\n".join(campaign.impact_points)),
        risks=escape("\n".join(campaign.risk_flags)),
        missing=escape("\n".join(campaign.missing_info)),
        snippets=escape("\n".join(campaign.source_snippets)),
        status_options=donor_campaign_status_options(campaign.status),
        review_options=offer_review_options(campaign.review_state),
        owner=escape(campaign.owner, quote=True),
        notes=escape(campaign.notes),
    )


def render_analyze_form(opportunity_id: str) -> str:
    return (
        "<section>"
        "<h2>Разобрать страницу</h2>"
        f"<form method=\"post\" action=\"/opportunities/{escape(opportunity_id)}/analyze\">"
        "<label>Текст источника, если страницу нельзя открыть автоматически"
        "<textarea name=\"source_text\" rows=\"7\" placeholder=\"Можно оставить пустым, тогда сервис попробует открыть ссылку\"></textarea>"
        "</label>"
        "<button type=\"submit\">Разобрать</button>"
        "</form>"
        "</section>"
    )


def render_b2b_analyze_form(lead_id: str) -> str:
    return (
        "<section>"
        "<h2>Разобрать B2B-источник</h2>"
        f"<form method=\"post\" action=\"/b2b/{escape(lead_id)}/analyze\">"
        "<label>Текст источника"
        "<textarea name=\"source_text\" rows=\"7\" placeholder=\"Вставьте текст со страницы компании, описания CSR или контактов\"></textarea>"
        "</label>"
        "<button type=\"submit\">Разобрать</button>"
        "</form>"
        "</section>"
    )


def render_blogger_analyze_form(lead_id: str) -> str:
    return (
        "<section>"
        "<h2>Разобрать публичный источник</h2>"
        f"<form method=\"post\" action=\"/bloggers/{escape(lead_id)}/analyze\">"
        "<label>Текст источника"
        "<textarea name=\"source_text\" rows=\"7\" placeholder=\"Вставьте публичное описание блога, сообщества или коллаборации\"></textarea>"
        "</label>"
        "<button type=\"submit\">Разобрать</button>"
        "</form>"
        "</section>"
    )


def status_options(current: str) -> str:
    statuses = {
        "needs_review": "Нужна проверка",
        "discovered": "Новая находка",
        "not_started": "Не начато",
        "accepted": "Принято",
        "rejected": "Отклонено",
    }
    return "".join(option(value, label, current) for value, label in statuses.items())


def review_state_options(current: str) -> str:
    states = {
        "needs_review": "Нужно проверить",
        "needs_clarification": "Нужно уточнить",
        "ready_for_human": "Готово к ручной проверке",
        "reviewed": "Проверено человеком",
    }
    return "".join(option(value, label, current) for value, label in states.items())


def readiness_state_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in READINESS_STATE_LABELS.items())


def lead_category_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in LEAD_CATEGORIES.items())


def lead_status_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in LEAD_STATUSES.items())


def offer_type_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in OFFER_TYPES.items())


def offer_status_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in OFFER_STATUSES.items())


def offer_review_options(current: str) -> str:
    states = {
        "needs_review": "Нужно проверить",
        "approved": "Проверено",
        "needs_update": "Нужно обновить",
    }
    return "".join(option(value, label, current) for value, label in states.items())


def donor_campaign_type_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in DONOR_CAMPAIGN_TYPES.items())


def donor_campaign_status_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in DONOR_CAMPAIGN_STATUSES.items())


def application_status_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in APPLICATION_STATUS_LABELS.items())


def reporting_state_options(current: str) -> str:
    return "".join(option(value, label, current) for value, label in REPORTING_STATE_LABELS.items())


def feedback_status_options(current: str) -> str:
    states = {
        "new": "Новое",
        "reviewed": "Просмотрено",
        "converted_to_task": "Превращено в задачу",
        "ignored": "Не берем в работу",
    }
    return "".join(option(value, label, current or "new") for value, label in states.items())


def fund_wiki_review_options(current: str) -> str:
    states = {
        "approved": "Проверено",
        "needs_review": "Нужно проверить",
        "needs_update": "Нужно обновить",
    }
    return "".join(option(value, label, current) for value, label in states.items())


def option(value: str, label: str, current: str) -> str:
    selected = " selected" if value == current else ""
    return f"<option value=\"{escape(value)}\"{selected}>{escape(label)}</option>"


def render_application_status_form(application: Application, *, target: str) -> str:
    return (
        f"<form method=\"post\" action=\"{target}\">"
        f"<label>Стадия <select name=\"status\">{application_status_options(application.status)}</select></label>"
        f"<label>Ответственный <input name=\"owner\" value=\"{escape(application.owner, quote=True)}\" placeholder=\"Имя\"></label>"
        f"<label>Кто подал <input name=\"submitted_by\" value=\"{escape(application.submitted_by, quote=True)}\" placeholder=\"Имя, если уже подано\"></label>"
        "<button type=\"submit\">Сохранить стадию</button>"
        "</form>"
    )


def render_application_dates_form(application: Application, *, target: str) -> str:
    return (
        f"<form method=\"post\" action=\"{target}\">"
        f"<label>Дата подачи <input name=\"submitted_at\" value=\"{escape(application.submitted_at or '', quote=True)}\" placeholder=\"YYYY-MM-DD\"></label>"
        f"<label>Срок ответа <input name=\"response_due_at\" value=\"{escape(application.response_due_at or '', quote=True)}\" placeholder=\"YYYY-MM-DD\"></label>"
        f"<label>Срок отчета <input name=\"reporting_due_at\" value=\"{escape(application.reporting_due_at or '', quote=True)}\" placeholder=\"YYYY-MM-DD\"></label>"
        f"<label>Проверить позже <input name=\"recheck_at\" value=\"{escape(application.recheck_at or '', quote=True)}\" placeholder=\"YYYY-MM-DD\"></label>"
        "<button type=\"submit\">Сохранить сроки</button>"
        "</form>"
    )


def render_application_note_form(application: Application, *, target: str) -> str:
    return (
        f"<form method=\"post\" action=\"{target}\">"
        f"<label>Заметка по заявке<textarea name=\"notes\" rows=\"4\">{escape(application.notes)}</textarea></label>"
        "<button type=\"submit\">Сохранить заметку</button>"
        "</form>"
    )


def application_sort_key(application: Application) -> tuple[str, str]:
    return (application.response_due_at or application.reporting_due_at or application.recheck_at or "9999-12-31", application.id)


def render_application_blockers(application: Application) -> str:
    today = date.today().isoformat()
    blockers = []
    if not application.owner:
        blockers.append("нет ответственного")
    if application.response_due_at and application.response_due_at < today and application.status in {"submitted_by_human", "waiting_response"}:
        blockers.append("ответ просрочен")
    if (
        application.reporting_due_at
        and application.reporting_due_at < today
        and application.status == "reporting_needed"
        and application.reporting_state != "prepared_by_human"
    ):
        blockers.append("отчет просрочен")
    if application.recheck_at and application.status == "recheck_later":
        blockers.append("проверить позже")
    if not blockers:
        return ""
    return "<br>" + "".join(f"<span class=\"needs-info\">{escape(item)}</span><br>" for item in blockers)


def render_activity_log(activity: Iterable[ActivityLogEntry], *, empty_text: str) -> str:
    rows = list(activity)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    return "<ul>" + "".join(f"<li>{escape(item.timestamp)}: {escape(item.action)} — {escape(item.details)}</li>" for item in rows) + "</ul>"


def render_feedback_log(activity: Iterable[ActivityLogEntry]) -> str:
    feedback = [item for item in activity if item.action == "operator_feedback"]
    rows = []
    for item in feedback:
        status = item.status or "new"
        rows.append(
            "<tr>"
            f"<td>{escape(item.timestamp)}</td>"
            f"<td>{escape(item.details)}</td>"
            f"<td>{escape(status)}</td>"
            "<td>"
            f"<form method=\"post\" action=\"/feedback/{escape(item.id)}/status\">"
            f"<select name=\"status\">{feedback_status_options(status)}</select>"
            "<button type=\"submit\">Сохранить</button>"
            "</form>"
            "</td>"
            "</tr>"
        )
    table = (
        "<p class=\"muted\">Пока нет наблюдений.</p>"
        if not rows
        else "<table><thead><tr><th>Дата</th><th>Наблюдение</th><th>Статус</th><th>Действие</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return f"<section><h2>Журнал наблюдений</h2>{table}</section>"
