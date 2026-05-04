from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from balance_fundraising.domain import ActivityLogEntry, Application, FundWikiEntry, FundraisingLead, Opportunity, ServiceOffer

TABLES = ["Opportunities", "Applications", "Leads", "ServiceOffers", "FundWiki", "Documents", "ActivityLog"]

DEFAULT_FUND_WIKI = [
    FundWikiEntry(
        key="mission",
        value="Помогать людям с психическими расстройствами выстраивать путь к более стабильному состоянию и полноценной жизни.",
        source="Вики фонда",
    ),
    FundWikiEntry(
        key="audience",
        value="Взрослые люди с психическими расстройствами, их близкие, специалисты помогающих профессий.",
        source="Вики фонда",
    ),
    FundWikiEntry(
        key="programs",
        value="Равный равному, Социально-психологическая помощь, Сообщество.",
        source="Вики фонда",
    ),
    FundWikiEntry(
        key="started",
        value="Фонд работает с 2020 года.",
        source="Вики фонда",
    ),
    FundWikiEntry(
        key="safety",
        value="Фонд соблюдает безопасность, конфиденциальность, профессиональные границы и бережную коммуникацию.",
        source="Вики фонда",
    ),
]


class LocalJsonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def init_store(self) -> None:
        data = self._read()
        changed = False
        for table in TABLES:
            if table not in data:
                data[table] = []
                changed = True
        if not data["FundWiki"]:
            data["FundWiki"] = [entry.to_dict() for entry in DEFAULT_FUND_WIKI]
            changed = True
        if changed:
            self._write(data)

    def upsert_opportunity(self, opportunity: Opportunity) -> None:
        data = self._read_initialized()
        rows = data["Opportunities"]
        payload = opportunity.to_dict()
        for index, row in enumerate(rows):
            if row["id"] == opportunity.id:
                rows[index] = payload
                break
        else:
            rows.append(payload)
        self._write(data)

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        for opportunity in self.list_opportunities():
            if opportunity.id == opportunity_id:
                return opportunity
        raise KeyError(f"Opportunity not found: {opportunity_id}")

    def list_opportunities(self) -> List[Opportunity]:
        data = self._read_initialized()
        return [Opportunity.from_dict(row) for row in data["Opportunities"]]

    def update_opportunity_fields(self, opportunity_id: str, fields: Dict[str, object]) -> Opportunity:
        opportunity = self.get_opportunity(opportunity_id)
        for key, value in fields.items():
            if key not in Opportunity.__dataclass_fields__:
                raise KeyError(f"Unknown opportunity field: {key}")
            setattr(opportunity, key, value)
        self.upsert_opportunity(opportunity)
        return opportunity

    def upsert_application(self, application: Application) -> None:
        data = self._read_initialized()
        rows = data["Applications"]
        payload = application.to_dict()
        for index, row in enumerate(rows):
            if row["id"] == application.id:
                rows[index] = payload
                break
        else:
            rows.append(payload)
        self._write(data)

    def get_application(self, application_id: str) -> Application:
        for application in self.list_applications():
            if application.id == application_id:
                return application
        raise KeyError(f"Application not found: {application_id}")

    def list_applications(self) -> List[Application]:
        data = self._read_initialized()
        return [Application.from_dict(row) for row in data["Applications"]]

    def update_application_fields(self, application_id: str, fields: Dict[str, object]) -> Application:
        application = self.get_application(application_id)
        for key, value in fields.items():
            if key not in Application.__dataclass_fields__:
                raise KeyError(f"Unknown application field: {key}")
            setattr(application, key, value)
        self.upsert_application(application)
        return application

    def upsert_lead(self, lead: FundraisingLead) -> None:
        data = self._read_initialized()
        rows = data["Leads"]
        payload = lead.to_dict()
        for index, row in enumerate(rows):
            if row["id"] == lead.id:
                rows[index] = payload
                break
        else:
            rows.append(payload)
        self._write(data)

    def get_lead(self, lead_id: str) -> FundraisingLead:
        for lead in self.list_leads():
            if lead.id == lead_id:
                return lead
        raise KeyError(f"Lead not found: {lead_id}")

    def list_leads(self) -> List[FundraisingLead]:
        data = self._read_initialized()
        return [FundraisingLead.from_dict(row) for row in data["Leads"]]

    def update_lead_fields(self, lead_id: str, fields: Dict[str, object]) -> FundraisingLead:
        lead = self.get_lead(lead_id)
        for key, value in fields.items():
            if key not in FundraisingLead.__dataclass_fields__:
                raise KeyError(f"Unknown lead field: {key}")
            setattr(lead, key, value)
        self.upsert_lead(lead)
        return lead

    def upsert_service_offer(self, offer: ServiceOffer) -> None:
        data = self._read_initialized()
        rows = data["ServiceOffers"]
        payload = offer.to_dict()
        for index, row in enumerate(rows):
            if row["id"] == offer.id:
                rows[index] = payload
                break
        else:
            rows.append(payload)
        self._write(data)

    def get_service_offer(self, offer_id: str) -> ServiceOffer:
        for offer in self.list_service_offers():
            if offer.id == offer_id:
                return offer
        raise KeyError(f"Service offer not found: {offer_id}")

    def list_service_offers(self) -> List[ServiceOffer]:
        data = self._read_initialized()
        return [ServiceOffer.from_dict(row) for row in data["ServiceOffers"]]

    def update_service_offer_fields(self, offer_id: str, fields: Dict[str, object]) -> ServiceOffer:
        offer = self.get_service_offer(offer_id)
        for key, value in fields.items():
            if key not in ServiceOffer.__dataclass_fields__:
                raise KeyError(f"Unknown service offer field: {key}")
            setattr(offer, key, value)
        self.upsert_service_offer(offer)
        return offer

    def list_fund_wiki(self) -> List[FundWikiEntry]:
        data = self._read_initialized()
        return [FundWikiEntry.from_dict(row) for row in data["FundWiki"]]

    def upsert_fund_wiki_entry(self, entry: FundWikiEntry) -> None:
        data = self._read_initialized()
        rows = data["FundWiki"]
        payload = entry.to_dict()
        for index, row in enumerate(rows):
            if row["key"] == entry.key:
                rows[index] = payload
                break
        else:
            rows.append(payload)
        self._write(data)

    def add_activity(self, entry: ActivityLogEntry) -> None:
        data = self._read_initialized()
        if not entry.id:
            entry = ActivityLogEntry.from_dict(entry.to_dict())
        data["ActivityLog"].append(entry.to_dict())
        self._write(data)

    def list_activity(self) -> List[ActivityLogEntry]:
        data = self._read_initialized()
        return [ActivityLogEntry.from_dict(row) for row in data["ActivityLog"]]

    def update_activity_fields(self, activity_id: str, fields: Dict[str, object]) -> ActivityLogEntry:
        data = self._read_initialized()
        rows = data["ActivityLog"]
        for index, row in enumerate(rows):
            entry = ActivityLogEntry.from_dict(row)
            if entry.id == activity_id:
                for key, value in fields.items():
                    if key not in ActivityLogEntry.__dataclass_fields__:
                        raise KeyError(f"Unknown activity field: {key}")
                    setattr(entry, key, value)
                rows[index] = entry.to_dict()
                self._write(data)
                return entry
        raise KeyError(f"Activity not found: {activity_id}")

    def _read_initialized(self) -> Dict[str, Any]:
        self.init_store()
        return self._read()

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {table: [] for table in TABLES}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
