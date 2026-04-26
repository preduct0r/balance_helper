from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


def opportunity_id_for_url(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"opp_{digest}"


@dataclass
class Opportunity:
    id: str
    url: str
    name: str = "[НУЖНО УТОЧНИТЬ]"
    organization: str = "[НУЖНО УТОЧНИТЬ]"
    type: str = "unknown"
    deadline: Optional[str] = None
    status: str = "needs_review"
    eligibility: List[str] = field(default_factory=list)
    required_documents: List[str] = field(default_factory=list)
    application_url: Optional[str] = None
    contact: Optional[str] = None
    reporting_requirements: List[str] = field(default_factory=list)
    fit_for_fund: str = "unknown"
    missing_info: List[str] = field(default_factory=list)
    source_snippets: List[str] = field(default_factory=list)
    confidence: float = 0.0
    next_action: str = "Проверить человеком"
    owner: str = ""
    last_checked: Optional[str] = None

    @classmethod
    def from_url(cls, url: str) -> "Opportunity":
        return cls(id=opportunity_id_for_url(url), url=url)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        values = dict(data)
        if "source_url" in values and "url" not in values:
            values["url"] = values.pop("source_url")
        return cls(**{field_name: values.get(field_name) for field_name in cls.__dataclass_fields__})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Application:
    id: str
    opportunity_id: str
    status: str = "not_started"
    submitted_at: Optional[str] = None
    response_due_at: Optional[str] = None
    reporting_due_at: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundWikiEntry:
    key: str
    value: str
    source: str = "FundWiki"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentRecord:
    name: str
    status: str = "unknown"
    url: str = ""
    updated_at: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActivityLogEntry:
    timestamp: str
    action: str
    entity_id: str
    details: str = ""

    @classmethod
    def today(cls, *, action: str, entity_id: str, details: str = "") -> "ActivityLogEntry":
        return cls(timestamp=date.today().isoformat(), action=action, entity_id=entity_id, details=details)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

