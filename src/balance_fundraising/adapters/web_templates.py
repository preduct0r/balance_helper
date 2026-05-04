from __future__ import annotations

from datetime import date
from html import escape
from typing import Iterable, List

from balance_fundraising.adapters.web_static import WEB_CSS
from balance_fundraising.domain import ActivityLogEntry, Application, FundWikiEntry, Opportunity
from balance_fundraising.services.applications import (
    APPLICATION_STATUS_LABELS,
    REPORTING_STATE_LABELS,
    application_status_label,
    reporting_state_label,
)
from balance_fundraising.services.fund_wiki import REQUIRED_FUND_WIKI_FIELDS, fund_wiki_by_key, fund_wiki_label
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
    <nav><a href="/">Рабочий стол</a><a href="/radar">Радар</a><a href="/opportunities">Возможности</a><a href="/applications">Заявки</a><a href="/review">Проверка</a><a href="/fund-wiki">Паспорт фонда</a><a href="/first-run">Первый прогон</a></nav>
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


def render_review_queue_page(opportunities: Iterable[Opportunity]) -> str:
    body = [
        "<section>",
        "<h2>Очередь проверки</h2>",
        "<p class=\"muted\">Здесь собраны новые находки, результаты разбора и черновики, которые нельзя использовать вовне без человека.</p>",
        render_opportunity_table(opportunities, empty_text="Пока нечего проверять."),
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
