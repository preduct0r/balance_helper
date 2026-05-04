from __future__ import annotations

from typing import Dict, List

from balance_fundraising.adapters.local_json_store import DEFAULT_FUND_WIKI, TABLES
from balance_fundraising.domain import ActivityLogEntry, Application, FundWikiEntry, FundraisingLead, Opportunity, ServiceOffer


class GoogleSheetsStore:
    """Google Sheets adapter with a small gspread-based implementation.

    Tests use LocalJsonStore. This adapter is intentionally thin and lazy-loads
    gspread so local development does not require Google credentials.
    """

    def __init__(self, spreadsheet_id: str, service_account_file: str) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.service_account_file = service_account_file
        self._spreadsheet = None
        self._initialized = False

    def init_store(self) -> None:
        spreadsheet = self._open()
        existing = {worksheet.title for worksheet in spreadsheet.worksheets()}
        for table in TABLES:
            if table not in existing:
                spreadsheet.add_worksheet(title=table, rows=1000, cols=30)
        self._initialized = True
        if not self._records("FundWiki"):
            for entry in DEFAULT_FUND_WIKI:
                self.upsert_fund_wiki_entry(entry)

    def upsert_opportunity(self, opportunity: Opportunity) -> None:
        self._upsert_row("Opportunities", "id", opportunity.to_dict())

    def get_opportunity(self, opportunity_id: str) -> Opportunity:
        for opportunity in self.list_opportunities():
            if opportunity.id == opportunity_id:
                return opportunity
        raise KeyError(f"Opportunity not found: {opportunity_id}")

    def list_opportunities(self) -> List[Opportunity]:
        return [Opportunity.from_dict(row) for row in self._records("Opportunities")]

    def update_opportunity_fields(self, opportunity_id: str, fields: Dict[str, object]) -> Opportunity:
        opportunity = self.get_opportunity(opportunity_id)
        for key, value in fields.items():
            setattr(opportunity, key, value)
        self.upsert_opportunity(opportunity)
        return opportunity

    def upsert_application(self, application: Application) -> None:
        self._upsert_row("Applications", "id", application.to_dict())

    def get_application(self, application_id: str) -> Application:
        for application in self.list_applications():
            if application.id == application_id:
                return application
        raise KeyError(f"Application not found: {application_id}")

    def list_applications(self) -> List[Application]:
        return [Application.from_dict(row) for row in self._records("Applications") if row.get("id")]

    def update_application_fields(self, application_id: str, fields: Dict[str, object]) -> Application:
        application = self.get_application(application_id)
        for key, value in fields.items():
            setattr(application, key, value)
        self.upsert_application(application)
        return application

    def upsert_lead(self, lead: FundraisingLead) -> None:
        self._upsert_row("Leads", "id", lead.to_dict())

    def get_lead(self, lead_id: str) -> FundraisingLead:
        for lead in self.list_leads():
            if lead.id == lead_id:
                return lead
        raise KeyError(f"Lead not found: {lead_id}")

    def list_leads(self) -> List[FundraisingLead]:
        return [FundraisingLead.from_dict(row) for row in self._records("Leads") if row.get("id")]

    def update_lead_fields(self, lead_id: str, fields: Dict[str, object]) -> FundraisingLead:
        lead = self.get_lead(lead_id)
        for key, value in fields.items():
            setattr(lead, key, value)
        self.upsert_lead(lead)
        return lead

    def upsert_service_offer(self, offer: ServiceOffer) -> None:
        self._upsert_row("ServiceOffers", "id", offer.to_dict())

    def get_service_offer(self, offer_id: str) -> ServiceOffer:
        for offer in self.list_service_offers():
            if offer.id == offer_id:
                return offer
        raise KeyError(f"Service offer not found: {offer_id}")

    def list_service_offers(self) -> List[ServiceOffer]:
        return [ServiceOffer.from_dict(row) for row in self._records("ServiceOffers") if row.get("id")]

    def update_service_offer_fields(self, offer_id: str, fields: Dict[str, object]) -> ServiceOffer:
        offer = self.get_service_offer(offer_id)
        for key, value in fields.items():
            setattr(offer, key, value)
        self.upsert_service_offer(offer)
        return offer

    def list_fund_wiki(self) -> List[FundWikiEntry]:
        return [FundWikiEntry.from_dict(row) for row in self._records("FundWiki") if row.get("key")]

    def upsert_fund_wiki_entry(self, entry: FundWikiEntry) -> None:
        self._upsert_row("FundWiki", "key", entry.to_dict())

    def add_activity(self, entry: ActivityLogEntry) -> None:
        if not entry.id:
            entry = ActivityLogEntry.from_dict(entry.to_dict())
        worksheet = self._worksheet("ActivityLog")
        self._ensure_headers(worksheet, list(entry.to_dict().keys()))
        worksheet.append_row(list(entry.to_dict().values()))

    def list_activity(self) -> List[ActivityLogEntry]:
        return [ActivityLogEntry.from_dict(row) for row in self._records("ActivityLog")]

    def update_activity_fields(self, activity_id: str, fields: Dict[str, object]) -> ActivityLogEntry:
        worksheet = self._worksheet("ActivityLog")
        records = worksheet.get_all_records()
        for index, row in enumerate(records, start=2):
            entry = ActivityLogEntry.from_dict(row)
            if entry.id == activity_id:
                for key, value in fields.items():
                    setattr(entry, key, value)
                payload = entry.to_dict()
                headers = list(payload.keys())
                self._ensure_headers(worksheet, headers)
                worksheet.update(f"A{index}", [[self._cell_value(payload.get(header)) for header in headers]])
                return entry
        raise KeyError(f"Activity not found: {activity_id}")

    def _open(self):
        if self._spreadsheet is None:
            try:
                import gspread
            except ImportError as exc:
                raise RuntimeError("Install the google extra to use GoogleSheetsStore: pip install .[google]") from exc
            client = gspread.service_account(filename=self.service_account_file)
            self._spreadsheet = client.open_by_key(self.spreadsheet_id)
        return self._spreadsheet

    def _worksheet(self, title: str):
        if not self._initialized:
            self.init_store()
        return self._open().worksheet(title)

    def _records(self, title: str) -> List[Dict[str, str]]:
        worksheet = self._worksheet(title)
        return worksheet.get_all_records()

    def _upsert_row(self, title: str, key: str, payload: Dict[str, object]) -> None:
        worksheet = self._worksheet(title)
        headers = list(payload.keys())
        self._ensure_headers(worksheet, headers)
        records = worksheet.get_all_records()
        row_values = [self._cell_value(payload.get(header)) for header in headers]
        for index, row in enumerate(records, start=2):
            if str(row.get(key)) == str(payload[key]):
                worksheet.update(f"A{index}", [row_values])
                return
        worksheet.append_row(row_values)

    def _ensure_headers(self, worksheet, headers: List[str]) -> None:
        existing = worksheet.row_values(1)
        if not existing:
            worksheet.update("A1", [headers])
        elif existing != headers:
            merged = existing + [header for header in headers if header not in existing]
            worksheet.update("A1", [merged])

    def _cell_value(self, value: object) -> str:
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        if value is None:
            return ""
        return str(value)
