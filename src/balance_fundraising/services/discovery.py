from __future__ import annotations

from typing import Iterable, List

from balance_fundraising.app_defaults import DEFAULT_DISCOVERY_QUERIES
from balance_fundraising.domain import ActivityLogEntry, Opportunity


class DiscoveryService:
    def __init__(self, store, search_client) -> None:
        self.store = store
        self.search_client = search_client

    def discover(self, queries: Iterable[str] | None = None, *, limit_per_query: int = 10) -> List[Opportunity]:
        created: List[Opportunity] = []
        for query in queries or DEFAULT_DISCOVERY_QUERIES:
            for result in self.search_client.search(query, groups_on_page=limit_per_query):
                opportunity = Opportunity.from_url(result.url)
                opportunity.name = result.title or opportunity.name
                opportunity.source_snippets = [result.snippet] if result.snippet else []
                opportunity.status = "discovered"
                opportunity.next_action = "Проанализировать страницу и подтвердить релевантность"
                self.store.upsert_opportunity(opportunity)
                self.store.add_activity(ActivityLogEntry.today(action="discover", entity_id=opportunity.id, details=query))
                created.append(opportunity)
        return created

