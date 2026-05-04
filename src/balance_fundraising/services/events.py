from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List

from balance_fundraising.app_defaults import DEFAULT_EVENT_QUERIES
from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, FundraisingLead

MISSING = "[НУЖНО УТОЧНИТЬ]"


@dataclass
class EventDiscoveryRunResult:
    queries: List[str]
    created_count: int = 0
    existing_count: int = 0
    status: str = "completed"
    error: str = ""
    leads: List[FundraisingLead] = field(default_factory=list)


class EventDiscoveryService:
    def __init__(self, store, search_client) -> None:
        self.store = store
        self.search_client = search_client

    def discover(self, queries: Iterable[str] | None = None, *, limit_per_query: int = 10) -> EventDiscoveryRunResult:
        query_list = [query for query in (queries or DEFAULT_EVENT_QUERIES) if query]
        run = EventDiscoveryRunResult(queries=query_list)
        for query in query_list:
            try:
                results = self.search_client.search(query, groups_on_page=limit_per_query)
            except Exception as exc:
                run.status = "failed"
                run.error = sanitize_event_error(str(exc))
                self.store.add_activity(
                    ActivityLogEntry.today(action="event_discover_error", entity_id="event", details=f"{query}: {run.error}")
                )
                continue
            for result in results:
                lead, existed = self._lead_for_result(result.title, result.url, result.snippet)
                run.existing_count += 1 if existed else 0
                run.created_count += 0 if existed else 1
                lead.last_checked = date.today().isoformat()
                lead.next_action = "Проверить условия участия и чек-лист мероприятия"
                if result.snippet:
                    lead.source_snippets = [result.snippet]
                self.store.upsert_lead(lead)
                self.store.add_activity(ActivityLogEntry.today(action="event_discover", entity_id=lead.id, details=query))
                run.leads.append(lead)
        self.store.add_activity(
            ActivityLogEntry.today(
                action="event_discover_run",
                entity_id="event",
                details=(
                    f"{run.status}: queries={len(query_list)} created={run.created_count} "
                    f"existing={run.existing_count} limit={limit_per_query}"
                ),
            )
        )
        return run

    def _lead_for_result(self, title: str, url: str, snippet: str) -> tuple[FundraisingLead, bool]:
        candidate = FundraisingLead.from_values(
            category="event",
            name=title or MISSING,
            url=url,
            description=snippet,
        )
        for lead in self.store.list_leads():
            same_url = bool(url and lead.url == url)
            same_name = bool(title and lead.category == "event" and lead.name.lower() == title.lower())
            if lead.category == "event" and (same_url or same_name):
                return lead, True
        return candidate, False


def create_event_lead(store, *, name: str, url: str = "", description: str = "") -> FundraisingLead:
    lead = FundraisingLead.from_values(
        category="event",
        name=name,
        url=url,
        description=description,
    )
    lead.next_action = "Проверить условия участия и чек-лист мероприятия"
    store.upsert_lead(lead)
    store.add_activity(ActivityLogEntry.today(action="event_add", entity_id=lead.id, details=lead.name))
    return lead


def build_event_checklist(lead: FundraisingLead, fund_wiki: Iterable[FundWikiEntry]) -> str:
    wiki = {entry.key: entry.value for entry in fund_wiki if entry.review_state == "approved" and entry.value}
    mission = wiki.get("mission", MISSING)
    programs = wiki.get("programs", MISSING)
    evidence = "; ".join(lead.source_snippets) if lead.source_snippets else MISSING
    missing_info = "; ".join(lead.missing_info) if lead.missing_info else MISSING
    return "\n".join(
        [
            "Чек-лист мероприятия",
            "Нужна ручная проверка перед заявкой, контактом с организаторами или публикацией.",
            "",
            f"- Мероприятие: {lead.name or MISSING}",
            f"- Источник: {lead.url or MISSING}",
            f"- Дедлайн заявки: {lead.deadline or MISSING}",
            f"- Стоимость/взнос: {MISSING}",
            f"- Документы: {MISSING}",
            f"- Описание фонда: {mission}",
            f"- Программы фонда: {programs}",
            f"- Мерч и материалы: {MISSING}",
            f"- Волонтерские смены: {MISSING}",
            f"- Логистика: {MISSING}",
            f"- Пост-отчет: {MISSING}",
            f"- Что неизвестно: {missing_info}",
            f"- Подтверждения: {evidence}",
            "",
            "Границы v1: без складского учета, продаж, платежей, расчета остатков и автоматической подачи заявки.",
        ]
    )


def sanitize_event_error(message: str) -> str:
    sanitized = message
    for key in ["YANDEX_API_KEY", "YANDEX_FOLDER_ID"]:
        value = os.getenv(key)
        if value:
            sanitized = sanitized.replace(value, "[скрыто]")
    sanitized = sanitized.replace("SECRET", "[скрыто]")
    return sanitized
