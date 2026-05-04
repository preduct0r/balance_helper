from __future__ import annotations

from html import escape
from typing import Iterable, List

from balance_fundraising.adapters.web_static import WEB_CSS
from balance_fundraising.domain import Opportunity

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
    <nav><a href="/">Рабочий стол</a><a href="/opportunities">Возможности</a><a href="/review">Проверка</a></nav>
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


def render_review_queue_page(opportunities: Iterable[Opportunity]) -> str:
    body = [
        "<section>",
        "<h2>Очередь проверки</h2>",
        "<p class=\"muted\">Здесь собраны новые находки, результаты разбора и черновики, которые нельзя использовать вовне без человека.</p>",
        render_opportunity_table(opportunities, empty_text="Пока нечего проверять."),
        "</section>",
    ]
    return render_layout("Проверка", "\n".join(body))


def render_opportunity_detail_page(
    *,
    opportunity: Opportunity,
    checklist: str,
    draft: str,
    checklist_items: List[str],
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


def option(value: str, label: str, current: str) -> str:
    selected = " selected" if value == current else ""
    return f"<option value=\"{escape(value)}\"{selected}>{escape(label)}</option>"
