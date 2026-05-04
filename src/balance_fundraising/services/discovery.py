from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List

from balance_fundraising.app_defaults import DEFAULT_DISCOVERY_QUERIES
from balance_fundraising.domain import ActivityLogEntry, Opportunity


@dataclass
class DiscoveryRunResult:
    queries: List[str]
    created_count: int = 0
    existing_count: int = 0
    status: str = "completed"
    error: str = ""
    opportunities: List[Opportunity] = field(default_factory=list)


class DiscoveryService:
    def __init__(self, store, search_client) -> None:
        self.store = store
        self.search_client = search_client

    def discover(self, queries: Iterable[str] | None = None, *, limit_per_query: int = 10) -> DiscoveryRunResult:
        query_list = [query for query in (queries or DEFAULT_DISCOVERY_QUERIES) if query]
        run = DiscoveryRunResult(queries=query_list)
        for query in query_list:
            try:
                results = self.search_client.search(query, groups_on_page=limit_per_query)
            except Exception as exc:
                run.status = "failed"
                run.error = sanitize_discovery_error(str(exc))
                self.store.add_activity(ActivityLogEntry.today(action="discover_error", entity_id="radar", details=f"{query}: {run.error}"))
                continue
            for result in results:
                opportunity = Opportunity.from_url(result.url)
                try:
                    opportunity = self.store.get_opportunity(opportunity.id)
                    run.existing_count += 1
                except KeyError:
                    opportunity.name = result.title or opportunity.name
                    opportunity.status = "discovered"
                    run.created_count += 1
                if result.snippet:
                    opportunity.source_snippets = [result.snippet]
                opportunity.last_checked = date.today().isoformat()
                opportunity.next_action = "Проанализировать страницу и подтвердить релевантность"
                self.store.upsert_opportunity(opportunity)
                self.store.add_activity(ActivityLogEntry.today(action="discover", entity_id=opportunity.id, details=query))
                run.opportunities.append(opportunity)
        self.store.add_activity(
            ActivityLogEntry.today(
                action="discover_run",
                entity_id="radar",
                details=(
                    f"{run.status}: queries={len(query_list)} created={run.created_count} "
                    f"existing={run.existing_count} limit={limit_per_query}"
                ),
            )
        )
        return run


def sanitize_discovery_error(message: str) -> str:
    sanitized = message
    for key in ["YANDEX_API_KEY", "YANDEX_FOLDER_ID"]:
        value = os.getenv(key)
        if value:
            sanitized = sanitized.replace(value, "[скрыто]")
    sanitized = sanitized.replace("SECRET", "[скрыто]")
    return sanitized
