from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, Opportunity

TABLES = ["Opportunities", "Applications", "FundWiki", "Documents", "ActivityLog"]

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

    def list_fund_wiki(self) -> List[FundWikiEntry]:
        data = self._read_initialized()
        return [FundWikiEntry(**row) for row in data["FundWiki"]]

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
        data["ActivityLog"].append(entry.to_dict())
        self._write(data)

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

