from __future__ import annotations

from typing import Dict, List, Protocol

from balance_fundraising.domain import ActivityLogEntry, Application, FundWikiEntry, Opportunity


class Store(Protocol):
    def init_store(self) -> None:
        ...

    def upsert_opportunity(self, opportunity: Opportunity) -> None:
        ...

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        ...

    def list_opportunities(self) -> List[Opportunity]:
        ...

    def update_opportunity_fields(self, opportunity_id: str, fields: Dict[str, object]) -> Opportunity:
        ...

    def upsert_application(self, application: Application) -> None:
        ...

    def get_application(self, application_id: str) -> Application:
        ...

    def list_applications(self) -> List[Application]:
        ...

    def update_application_fields(self, application_id: str, fields: Dict[str, object]) -> Application:
        ...

    def list_fund_wiki(self) -> List[FundWikiEntry]:
        ...

    def upsert_fund_wiki_entry(self, entry: FundWikiEntry) -> None:
        ...

    def add_activity(self, entry: ActivityLogEntry) -> None:
        ...

    def list_activity(self) -> List[ActivityLogEntry]:
        ...
