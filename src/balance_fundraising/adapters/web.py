from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

from balance_fundraising.domain import ActivityLogEntry, Opportunity
from balance_fundraising.services.analysis import OpportunityAnalysisService
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.draft import build_application_draft

STATUS_LABELS = {
    "needs_review": "Нужна проверка",
    "discovered": "Новая находка",
    "not_started": "Не начато",
    "accepted": "Принято",
    "rejected": "Отклонено",
}


class WebApp:
    def __init__(self, store) -> None:
        self.store = store

    def render(self, path: str) -> tuple[int, str]:
        parsed = urlparse(path)
        route = parsed.path
        if route == "/":
            return 200, render_dashboard(self.store)
        if route == "/opportunities":
            return 200, render_opportunities(self.store.list_opportunities())
        if route.startswith("/opportunities/"):
            opportunity_id = unquote(route.removeprefix("/opportunities/")).strip("/")
            if "/" in opportunity_id or not opportunity_id:
                return 404, render_not_found()
            return 200, render_opportunity_detail(self.store, opportunity_id)
        return 404, render_not_found()

    def post(self, path: str, form: Dict[str, str]) -> tuple[int, str]:
        parsed = urlparse(path)
        route = parsed.path
        if route == "/opportunities":
            url = form.get("url", "").strip()
            if not url:
                return 400, render_message("Нужна ссылка", "Вставьте ссылку на страницу возможности.")
            opportunity = add_opportunity(self.store, url)
            return 303, f"/opportunities/{opportunity.id}"
        if route.startswith("/opportunities/") and route.endswith("/analyze"):
            opportunity_id = unquote(route.removeprefix("/opportunities/").removesuffix("/analyze")).strip("/")
            source_text = form.get("source_text", "").strip() or None
            analyze_opportunity(self.store, opportunity_id, source_text=source_text)
            return 303, f"/opportunities/{opportunity_id}"
        return 404, render_not_found()


def add_opportunity(store, url: str) -> Opportunity:
    opportunity = Opportunity.from_url(url)
    store.upsert_opportunity(opportunity)
    store.add_activity(ActivityLogEntry.today(action="add_link", entity_id=opportunity.id, details=url))
    return opportunity


def analyze_opportunity(store, opportunity_id: str, *, source_text: Optional[str] = None) -> Opportunity:
    return OpportunityAnalysisService(store).analyze_opportunity(opportunity_id, text=source_text, use_llm=False)


def render_dashboard(store) -> str:
    opportunities = store.list_opportunities()
    missing_deadlines = [item for item in opportunities if not item.deadline]
    new_items = [item for item in opportunities if item.status in {"needs_review", "discovered"}]
    body = [
        "<section>",
        "<h2>Сегодня важно</h2>",
        f"<pre>{escape(build_digest(opportunities))}</pre>",
        "</section>",
        "<section>",
        "<h2>Новые находки</h2>",
        render_opportunity_table(new_items, empty_text="Новых находок нет."),
        "</section>",
        "<section>",
        "<h2>Дедлайн нужно уточнить</h2>",
        render_opportunity_table(missing_deadlines, empty_text="Все дедлайны заполнены."),
        "</section>",
        render_add_link_form(),
    ]
    return render_layout("Рабочий стол фандрайзинга", "\n".join(body))


def render_opportunities(opportunities: Iterable[Opportunity]) -> str:
    body = [
        "<section>",
        "<h2>Все возможности</h2>",
        render_opportunity_table(opportunities, empty_text="Пока нет возможностей."),
        "</section>",
        render_add_link_form(),
    ]
    return render_layout("Возможности", "\n".join(body))


def render_opportunity_detail(store, opportunity_id: str) -> str:
    try:
        opportunity = store.get_opportunity(opportunity_id)
    except KeyError:
        return render_not_found()
    checklist = build_checklist(opportunity)
    draft = build_application_draft(opportunity, store.list_fund_wiki())
    body = [
        "<section>",
        f"<h2>{escape(opportunity.name)}</h2>",
        f"<p class=\"muted\">{escape(status_label(opportunity.status))}</p>",
        fact_row_html("Источник", link(opportunity.url)),
        fact_row("Дедлайн", opportunity.deadline or "[НУЖНО УТОЧНИТЬ]"),
        fact_row("Тип", opportunity.type),
        fact_row("Следующее действие", opportunity.next_action),
        fact_row("Уверенность", f"{opportunity.confidence:.2f}"),
        "</section>",
        "<section>",
        "<h2>Требования</h2>",
        render_list(opportunity.eligibility, empty_text="[НУЖНО УТОЧНИТЬ] Требования к участию"),
        "</section>",
        "<section>",
        "<h2>Документы</h2>",
        render_list(opportunity.required_documents, empty_text="[НУЖНО УТОЧНИТЬ] Список документов"),
        "</section>",
        "<section>",
        "<h2>Что нужно уточнить</h2>",
        render_list(opportunity.missing_info, empty_text="Нет отмеченных пробелов."),
        "</section>",
        "<section>",
        "<h2>Подтверждения из источника</h2>",
        render_list(opportunity.source_snippets, empty_text="Пока нет фрагментов источника."),
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


def render_opportunity_table(opportunities: Iterable[Opportunity], *, empty_text: str) -> str:
    rows = list(opportunities)
    if not rows:
        return f"<p class=\"muted\">{escape(empty_text)}</p>"
    body_rows = []
    for opportunity in rows:
        body_rows.append(
            "<tr>"
            f"<td><a href=\"/opportunities/{escape(opportunity.id)}\">{escape(opportunity.name)}</a></td>"
            f"<td>{escape(status_label(opportunity.status))}</td>"
            f"<td>{escape(opportunity.deadline or '[НУЖНО УТОЧНИТЬ]')}</td>"
            f"<td>{escape(opportunity.type)}</td>"
            f"<td>{escape(opportunity.next_action)}</td>"
            "</tr>"
        )
    return (
        "<table>"
        "<thead><tr><th>Название</th><th>Статус</th><th>Дедлайн</th><th>Тип</th><th>Следующее действие</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


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


def render_list(items: Iterable[str], *, empty_text: str) -> str:
    values = [item for item in items if item]
    if not values:
        return f"<p class=\"needs-info\">{escape(empty_text)}</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in values) + "</ul>"


def render_message(title: str, message: str) -> str:
    return render_layout(title, f"<section><h2>{escape(title)}</h2><p>{escape(message)}</p></section>")


def render_not_found() -> str:
    return render_message("Не найдено", "Такой страницы или записи нет.")


def render_layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, sans-serif; }}
    body {{ margin: 0; background: #f5f7f8; color: #172026; }}
    header {{ background: #ffffff; border-bottom: 1px solid #d9e1e5; padding: 18px 28px; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 24px; }}
    nav a {{ margin-right: 16px; color: #185a7d; text-decoration: none; font-weight: 600; }}
    section {{ background: #ffffff; border: 1px solid #d9e1e5; border-radius: 8px; margin-bottom: 18px; padding: 18px; }}
    h1 {{ margin: 0 0 10px; font-size: 28px; }}
    h2 {{ margin-top: 0; font-size: 20px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #e8eef1; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f0f4f6; }}
    input, textarea {{ width: 100%; box-sizing: border-box; margin-top: 6px; padding: 10px; border: 1px solid #bcc9cf; border-radius: 6px; font: inherit; }}
    button {{ margin-top: 10px; padding: 10px 14px; border: 0; border-radius: 6px; background: #185a7d; color: #ffffff; font-weight: 700; cursor: pointer; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f8fafb; border: 1px solid #e0e7eb; border-radius: 6px; padding: 12px; }}
    .muted {{ color: #5f6f78; }}
    .needs-info {{ color: #8a4b00; font-weight: 700; }}
    .fact {{ display: grid; grid-template-columns: 180px 1fr; gap: 10px; margin: 8px 0; }}
    .fact strong {{ color: #3c4a51; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <nav><a href="/">Рабочий стол</a><a href="/opportunities">Возможности</a></nav>
  </header>
  <main>{body}</main>
</body>
</html>"""


def fact_row(label: str, value: str) -> str:
    return f"<div class=\"fact\"><strong>{escape(label)}</strong><span>{escape(value)}</span></div>"


def fact_row_html(label: str, value: str) -> str:
    return f"<div class=\"fact\"><strong>{escape(label)}</strong><span>{value}</span></div>"


def link(url: str) -> str:
    safe_url = escape(url, quote=True)
    return f"<a href=\"{safe_url}\" target=\"_blank\" rel=\"noreferrer\">{escape(url)}</a>"


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def make_handler(app: WebApp):
    class FundraisingHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            status, html = app.render(self.path)
            self._send_html(status, html)

        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            form = {key: values[0] for key, values in parse_qs(raw_body).items()}
            status, result = app.post(self.path, form)
            if status == 303:
                self.send_response(303)
                self.send_header("Location", result)
                self.end_headers()
                return
            self._send_html(status, result)

        def log_message(self, format: str, *args) -> None:
            return

        def _send_html(self, status: int, html: str) -> None:
            payload = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return FundraisingHandler


def run_web_server(store, *, host: str = "127.0.0.1", port: int = 8080) -> None:
    app = WebApp(store)
    server = ThreadingHTTPServer((host, port), make_handler(app))
    print(f"Web UI: http://{host}:{port}")
    server.serve_forever()
