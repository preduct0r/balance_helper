from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from balance_fundraising.app_defaults import DEFAULT_DISCOVERY_QUERIES
from balance_fundraising.adapters.web_templates import (
    render_application_detail_page,
    render_applications_page,
    render_dashboard_page,
    render_first_run_page,
    render_fund_wiki_page,
    render_lead_detail_page,
    render_lead_list_page,
    render_message,
    render_not_found,
    render_opportunity_detail_page,
    render_opportunity_list_page,
    render_radar_page,
    render_review_queue_page,
)
from balance_fundraising.clients.yandex_search import YandexSearchClient
from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, Opportunity
from balance_fundraising.services.analysis import OpportunityAnalysisService
from balance_fundraising.services.applications import (
    build_reporting_checklist,
    create_application_for_opportunity,
    update_application_dates,
    update_application_note,
    update_application_reporting,
    update_application_response,
    update_application_status,
    update_feedback_status,
)
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.discovery import DiscoveryService, sanitize_discovery_error
from balance_fundraising.services.draft import build_application_draft
from balance_fundraising.services.fund_wiki import REQUIRED_FUND_WIKI_FIELDS, fund_wiki_by_key
from balance_fundraising.services.leads import create_lead, update_lead_note, update_lead_owner, update_lead_status
from balance_fundraising.services.readiness import build_readiness


class WebApp:
    def __init__(self, store, *, search_client_factory=None) -> None:
        self.store = store
        self.search_client_factory = search_client_factory or YandexSearchClient

    def render(self, path: str) -> tuple[int, str]:
        parsed = urlparse(path)
        route = parsed.path
        if route == "/":
            return 200, render_dashboard(self.store)
        if route == "/radar":
            return 200, render_radar(self.store)
        if route == "/opportunities":
            return 200, render_opportunities(self.store.list_opportunities())
        if route == "/applications":
            return 200, render_applications(self.store)
        if route == "/leads":
            return 200, render_leads(self.store)
        if route.startswith("/leads/"):
            lead_id = unquote(route.removeprefix("/leads/")).strip("/")
            if "/" in lead_id or not lead_id:
                return 404, render_not_found()
            return 200, render_lead_detail(self.store, lead_id)
        if route.startswith("/applications/"):
            application_id = unquote(route.removeprefix("/applications/")).strip("/")
            if "/" in application_id or not application_id:
                return 404, render_not_found()
            return 200, render_application_detail(self.store, application_id)
        if route == "/review":
            return 200, render_review_queue(self.store)
        if route == "/fund-wiki":
            return 200, render_fund_wiki(self.store)
        if route == "/first-run":
            return 200, render_first_run(self.store)
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
        if route == "/fund-wiki":
            update_fund_wiki(self.store, form)
            return 303, "/fund-wiki"
        if route == "/first-run/feedback":
            add_operator_feedback(self.store, form.get("feedback", ""))
            return 303, "/first-run"
        if route == "/radar/run":
            run_radar(self.store, self.search_client_factory, form)
            return 303, "/radar"
        if route == "/leads":
            lead = create_lead(
                self.store,
                category=form.get("category", "b2b"),
                name=form.get("name", ""),
                organization=form.get("organization", ""),
                url=form.get("url", ""),
                description=form.get("description", ""),
            )
            return 303, f"/leads/{lead.id}"
        lead_action = _parse_lead_action(route)
        if lead_action is not None:
            lead_id, action_name = lead_action
            if action_name == "status":
                update_lead_status(
                    self.store,
                    lead_id,
                    status=form.get("status", "needs_review"),
                    review_state=form.get("review_state", "needs_review"),
                )
            elif action_name == "owner":
                update_lead_owner(self.store, lead_id, form.get("owner", ""))
            elif action_name == "note":
                update_lead_note(self.store, lead_id, form.get("notes", ""))
            else:
                return 404, render_not_found()
            return 303, f"/leads/{lead_id}"
        feedback_action = _parse_feedback_action(route)
        if feedback_action is not None:
            activity_id, action_name = feedback_action
            if action_name != "status":
                return 404, render_not_found()
            update_feedback_status(self.store, activity_id, form.get("status", "new"))
            return 303, "/first-run"
        application_action = _parse_application_action(route)
        if application_action is not None:
            application_id, action_name = application_action
            if action_name == "status":
                update_application_status(
                    self.store,
                    application_id,
                    form.get("status", "preparing"),
                    owner=form.get("owner", ""),
                    submitted_by=form.get("submitted_by", ""),
                )
            elif action_name == "dates":
                update_application_dates(
                    self.store,
                    application_id,
                    submitted_at=form.get("submitted_at", ""),
                    response_due_at=form.get("response_due_at", ""),
                    reporting_due_at=form.get("reporting_due_at", ""),
                    recheck_at=form.get("recheck_at", ""),
                )
            elif action_name == "note":
                update_application_note(self.store, application_id, form.get("notes", ""))
            elif action_name == "response":
                update_application_response(
                    self.store,
                    application_id,
                    status=form.get("status", "waiting_response"),
                    response_summary=form.get("response_summary", ""),
                )
            elif action_name == "reporting":
                update_application_reporting(
                    self.store,
                    application_id,
                    reporting_state=form.get("reporting_state", "not_started"),
                    reporting_done_at=form.get("reporting_done_at", ""),
                    notes=form.get("notes", ""),
                )
            else:
                return 404, render_not_found()
            return 303, f"/applications/{application_id}"
        action = _parse_opportunity_action(route)
        if action is None:
            return 404, render_not_found()
        opportunity_id, action_name = action
        if action_name == "analyze":
            source_text = form.get("source_text", "").strip() or None
            analyze_opportunity(self.store, opportunity_id, source_text=source_text)
        elif action_name == "status":
            update_status(self.store, opportunity_id, status=form.get("status", ""), review_state=form.get("review_state", ""))
        elif action_name == "note":
            update_note(self.store, opportunity_id, form.get("notes", ""))
        elif action_name == "owner":
            update_owner(self.store, opportunity_id, form.get("owner", ""))
        elif action_name == "checklist":
            mark_checklist_done(self.store, opportunity_id, form.get("item", ""))
        elif action_name == "readiness":
            update_readiness(self.store, opportunity_id, form.get("readiness_state", ""))
        elif action_name == "application":
            create_application_for_opportunity(self.store, opportunity_id)
        else:
            return 404, render_not_found()
        return 303, f"/opportunities/{opportunity_id}"


def add_opportunity(store, url: str) -> Opportunity:
    opportunity = Opportunity.from_url(url)
    store.upsert_opportunity(opportunity)
    store.add_activity(ActivityLogEntry.today(action="add_link", entity_id=opportunity.id, details=url))
    return opportunity


def analyze_opportunity(store, opportunity_id: str, *, source_text: Optional[str] = None) -> Opportunity:
    opportunity = OpportunityAnalysisService(store).analyze_opportunity(opportunity_id, text=source_text, use_llm=False)
    opportunity.review_state = "needs_review"
    store.upsert_opportunity(opportunity)
    return opportunity


def update_status(store, opportunity_id: str, *, status: str, review_state: str) -> Opportunity:
    fields = {}
    if status:
        fields["status"] = status
    if review_state:
        fields["review_state"] = review_state
    opportunity = store.update_opportunity_fields(opportunity_id, fields)
    store.add_activity(ActivityLogEntry.today(action="status", entity_id=opportunity.id, details=f"{status} / {review_state}"))
    return opportunity


def update_note(store, opportunity_id: str, notes: str) -> Opportunity:
    opportunity = store.update_opportunity_fields(opportunity_id, {"notes": notes.strip()})
    store.add_activity(ActivityLogEntry.today(action="note", entity_id=opportunity.id, details="updated"))
    return opportunity


def update_owner(store, opportunity_id: str, owner: str) -> Opportunity:
    opportunity = store.update_opportunity_fields(opportunity_id, {"owner": owner.strip()})
    store.add_activity(ActivityLogEntry.today(action="owner", entity_id=opportunity.id, details=opportunity.owner))
    return opportunity


def mark_checklist_done(store, opportunity_id: str, item: str) -> Opportunity:
    opportunity = store.get_opportunity(opportunity_id)
    value = item.strip()
    if value and value not in opportunity.checklist_done:
        opportunity.checklist_done.append(value)
        store.upsert_opportunity(opportunity)
        store.add_activity(ActivityLogEntry.today(action="checklist_done", entity_id=opportunity.id, details=value))
    return opportunity


def update_readiness(store, opportunity_id: str, readiness_state: str) -> Opportunity:
    opportunity = store.update_opportunity_fields(opportunity_id, {"readiness_state": readiness_state.strip() or "not_started"})
    store.add_activity(ActivityLogEntry.today(action="readiness", entity_id=opportunity.id, details=opportunity.readiness_state))
    return opportunity


def update_fund_wiki(store, form: Dict[str, str]) -> None:
    key = form.get("key", "").strip()
    existing = fund_wiki_by_key(store.list_fund_wiki())
    fields = [field for field in REQUIRED_FUND_WIKI_FIELDS if field.key == key] if key else REQUIRED_FUND_WIKI_FIELDS
    for field in fields:
        current = existing.get(field.key, FundWikiEntry(key=field.key, value=""))
        value = form.get(f"value_{field.key}", current.value).strip()
        source = form.get(f"source_{field.key}", current.source).strip() or "FundWiki"
        owner = form.get(f"owner_{field.key}", current.owner).strip()
        review_state = form.get(f"review_state_{field.key}", current.review_state).strip() or "needs_review"
        entry = FundWikiEntry(
            key=field.key,
            value=value,
            source=source,
            owner=owner,
            review_state=review_state,
            last_updated=ActivityLogEntry.today(action="fund_wiki", entity_id=field.key).timestamp,
        )
        store.upsert_fund_wiki_entry(entry)
        store.add_activity(ActivityLogEntry.today(action="fund_wiki", entity_id=field.key, details=review_state))


def add_operator_feedback(store, feedback: str) -> None:
    value = feedback.strip()
    if value:
        store.add_activity(ActivityLogEntry.today(action="operator_feedback", entity_id="first-run", details=value))


def render_dashboard(store) -> str:
    opportunities = store.list_opportunities()
    missing_deadlines = [item for item in opportunities if not item.deadline]
    needs_review = review_queue_items(opportunities)
    drafts_with_gaps = [item for item in opportunities if item.missing_info or not item.deadline]
    return render_dashboard_page(
        needs_review=needs_review,
        missing_deadlines=missing_deadlines,
        drafts_with_gaps=drafts_with_gaps,
        digest_text=build_digest(opportunities, applications=store.list_applications(), leads=store.list_leads()),
    )


def render_radar(store) -> str:
    return render_radar_page(
        queries=DEFAULT_DISCOVERY_QUERIES,
        activity=store.list_activity(),
        opportunities=[item for item in store.list_opportunities() if item.status == "discovered"],
        yandex_configured=bool(os.getenv("YANDEX_API_KEY") and os.getenv("YANDEX_FOLDER_ID")),
    )


def run_radar(store, search_client_factory, form: Dict[str, str]) -> None:
    query = (form.get("custom_query", "").strip() or form.get("selected_query", "").strip() or form.get("query", "").strip())
    raw_limit = form.get("limit", "5").strip()
    try:
        limit = int(raw_limit)
    except ValueError:
        limit = 5
    limit = max(1, min(limit, 20))
    queries = [query] if query else None
    try:
        client = search_client_factory()
    except Exception as exc:
        error = sanitize_discovery_error(str(exc))
        store.add_activity(ActivityLogEntry.today(action="discover_error", entity_id="radar", details=error))
        store.add_activity(ActivityLogEntry.today(action="discover_run", entity_id="radar", details=f"failed: {error}"))
        return
    DiscoveryService(store, client).discover(queries, limit_per_query=limit)


def render_opportunities(opportunities: Iterable[Opportunity]) -> str:
    return render_opportunity_list_page(opportunities)


def render_applications(store) -> str:
    return render_applications_page(store.list_applications(), store.list_opportunities())


def render_leads(store) -> str:
    return render_lead_list_page(store.list_leads())


def render_lead_detail(store, lead_id: str) -> str:
    try:
        lead = store.get_lead(lead_id)
    except KeyError:
        return render_not_found()
    activity = [item for item in store.list_activity() if item.entity_id == lead.id]
    return render_lead_detail_page(lead, activity)


def render_application_detail(store, application_id: str) -> str:
    try:
        application = store.get_application(application_id)
        opportunity = store.get_opportunity(application.opportunity_id)
    except KeyError:
        return render_not_found()
    activity = [item for item in store.list_activity() if item.entity_id == application.id]
    return render_application_detail_page(
        application=application,
        opportunity=opportunity,
        reporting_checklist=build_reporting_checklist(application, opportunity),
        activity=activity,
    )


def render_review_queue(store) -> str:
    opportunities = review_queue_items(store.list_opportunities())
    leads = lead_review_queue_items(store.list_leads())
    return render_review_queue_page(opportunities, leads)


def render_fund_wiki(store) -> str:
    return render_fund_wiki_page(store.list_fund_wiki())


def render_opportunity_detail(store, opportunity_id: str) -> str:
    try:
        opportunity = store.get_opportunity(opportunity_id)
    except KeyError:
        return render_not_found()
    checklist = build_checklist(opportunity)
    wiki_entries = store.list_fund_wiki()
    draft = build_application_draft(opportunity, wiki_entries)
    checklist_items = opportunity.required_documents + opportunity.missing_info
    if not opportunity.deadline:
        checklist_items.append("Уточнить дедлайн")
    return render_opportunity_detail_page(
        opportunity=opportunity,
        applications=[item for item in store.list_applications() if item.opportunity_id == opportunity.id],
        checklist=checklist,
        draft=draft,
        checklist_items=checklist_items,
        readiness=build_readiness(opportunity, wiki_entries),
    )


def render_first_run(store) -> str:
    return render_first_run_page(store.list_activity())


def review_queue_items(opportunities: Iterable[Opportunity]) -> List[Opportunity]:
    return [
        item
        for item in opportunities
        if item.review_state != "reviewed" or item.status in {"needs_review", "discovered"} or bool(item.missing_info)
    ]


def lead_review_queue_items(leads) -> List[object]:
    return [
        item
        for item in leads
        if item.review_state != "reviewed" or item.status in {"needs_review"} or bool(item.missing_info) or bool(item.risk_flags)
    ]


def _parse_opportunity_action(route: str) -> Optional[tuple[str, str]]:
    if not route.startswith("/opportunities/"):
        return None
    parts = [part for part in route.split("/") if part]
    if len(parts) != 3:
        return None
    _, opportunity_id, action = parts
    return unquote(opportunity_id), action


def _parse_lead_action(route: str) -> Optional[tuple[str, str]]:
    if not route.startswith("/leads/"):
        return None
    parts = [part for part in route.split("/") if part]
    if len(parts) != 3:
        return None
    _, lead_id, action = parts
    return unquote(lead_id), action


def _parse_application_action(route: str) -> Optional[tuple[str, str]]:
    if not route.startswith("/applications/"):
        return None
    parts = [part for part in route.split("/") if part]
    if len(parts) != 3:
        return None
    _, application_id, action = parts
    return unquote(application_id), action


def _parse_feedback_action(route: str) -> Optional[tuple[str, str]]:
    if not route.startswith("/feedback/"):
        return None
    parts = [part for part in route.split("/") if part]
    if len(parts) != 3:
        return None
    _, activity_id, action = parts
    return unquote(activity_id), action


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
