from __future__ import annotations

import hashlib
from dataclasses import MISSING, asdict, dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


def opportunity_id_for_url(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"opp_{digest}"


def application_id_for_opportunity(opportunity_id: str) -> str:
    digest = hashlib.sha1(opportunity_id.encode("utf-8")).hexdigest()[:10]
    return f"app_{digest}"


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
    notes: str = ""
    checklist_done: List[str] = field(default_factory=list)
    review_state: str = "needs_review"
    readiness_state: str = "not_started"

    @classmethod
    def from_url(cls, url: str) -> "Opportunity":
        return cls(id=opportunity_id_for_url(url), url=url)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Opportunity":
        values = dict(data)
        if "source_url" in values and "url" not in values:
            values["url"] = values.pop("source_url")
        payload: Dict[str, Any] = {}
        list_fields = {
            "eligibility",
            "required_documents",
            "reporting_requirements",
            "missing_info",
            "source_snippets",
            "checklist_done",
        }
        for field_name, field_info in cls.__dataclass_fields__.items():
            if field_name not in values:
                continue
            value = values[field_name]
            if field_name in list_fields:
                value = _coerce_list(value)
            elif field_name == "confidence":
                value = _coerce_float(value)
            if value is None and field_info.default is not MISSING:
                continue
            payload[field_name] = value
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        return [part.strip() for part in value.splitlines() if part.strip()]
    return [str(value)]


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class Application:
    id: str
    opportunity_id: str
    status: str = "preparing"
    submitted_at: Optional[str] = None
    response_due_at: Optional[str] = None
    reporting_due_at: Optional[str] = None
    recheck_at: Optional[str] = None
    owner: str = ""
    next_action: str = "Подготовить заявку"
    submitted_by: str = ""
    status_updated_at: Optional[str] = None
    notes: str = ""

    @classmethod
    def from_opportunity(cls, opportunity_id: str) -> "Application":
        return cls(id=application_id_for_opportunity(opportunity_id), opportunity_id=opportunity_id)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Application":
        values = dict(data)
        payload: Dict[str, Any] = {}
        for field_name, field_info in cls.__dataclass_fields__.items():
            if field_name not in values:
                continue
            value = values[field_name]
            if value is None and field_info.default is not MISSING:
                continue
            payload[field_name] = value
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FundWikiEntry:
    key: str
    value: str
    source: str = "FundWiki"
    last_updated: Optional[str] = None
    owner: str = ""
    review_state: str = "approved"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FundWikiEntry":
        values = dict(data)
        payload: Dict[str, Any] = {}
        for field_name, field_info in cls.__dataclass_fields__.items():
            if field_name not in values:
                continue
            value = values[field_name]
            if value is None and field_info.default is not MISSING:
                continue
            payload[field_name] = value
        return cls(**payload)

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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityLogEntry":
        values = dict(data)
        payload: Dict[str, Any] = {}
        for field_name, field_info in cls.__dataclass_fields__.items():
            if field_name not in values:
                continue
            value = values[field_name]
            if value is None and field_info.default is not MISSING:
                continue
            payload[field_name] = value
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
