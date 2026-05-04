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


def lead_id_for_values(category: str, name: str, url: str = "", organization: str = "") -> str:
    source = url or f"{name}|{organization}"
    digest = hashlib.sha1(f"{category}|{source}".encode("utf-8")).hexdigest()[:10]
    return f"lead_{digest}"


def service_offer_id_for_values(name: str, offer_type: str) -> str:
    digest = hashlib.sha1(f"{offer_type}|{name}".encode("utf-8")).hexdigest()[:10]
    return f"offer_{digest}"


def donor_campaign_id_for_values(name: str, campaign_type: str, segment: str = "") -> str:
    digest = hashlib.sha1(f"{campaign_type}|{segment}|{name}".encode("utf-8")).hexdigest()[:10]
    return f"donor_{digest}"


def activity_id_for_values(timestamp: str, action: str, entity_id: str, details: str) -> str:
    digest = hashlib.sha1(f"{timestamp}|{action}|{entity_id}|{details}".encode("utf-8")).hexdigest()[:10]
    return f"act_{digest}"


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
    response_summary: str = ""
    reporting_state: str = "not_started"
    reporting_done_at: Optional[str] = None

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
class FundraisingLead:
    id: str
    category: str
    name: str = "[НУЖНО УТОЧНИТЬ]"
    organization: str = "[НУЖНО УТОЧНИТЬ]"
    url: str = ""
    description: str = ""
    status: str = "needs_review"
    fit_for_fund: str = "unknown"
    risk_flags: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    source_snippets: List[str] = field(default_factory=list)
    contact: str = ""
    owner: str = ""
    next_action: str = "Проверить человеком"
    deadline: Optional[str] = None
    recheck_at: Optional[str] = None
    last_checked: Optional[str] = None
    notes: str = ""
    review_state: str = "needs_review"
    confidence: float = 0.0

    @classmethod
    def from_values(
        cls,
        *,
        category: str,
        name: str,
        organization: str = "",
        url: str = "",
        description: str = "",
    ) -> "FundraisingLead":
        return cls(
            id=lead_id_for_values(category, name, url, organization),
            category=category,
            name=name or "[НУЖНО УТОЧНИТЬ]",
            organization=organization or "[НУЖНО УТОЧНИТЬ]",
            url=url,
            description=description,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FundraisingLead":
        values = dict(data)
        payload: Dict[str, Any] = {}
        list_fields = {"risk_flags", "missing_info", "source_snippets"}
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


@dataclass
class ServiceOffer:
    id: str
    name: str = "[НУЖНО УТОЧНИТЬ]"
    offer_type: str = "educational_product"
    audience: str = ""
    format: str = ""
    value_proposition: str = ""
    requirements: List[str] = field(default_factory=list)
    materials_needed: List[str] = field(default_factory=list)
    status: str = "needs_review"
    owner: str = ""
    notes: str = ""
    review_state: str = "needs_review"
    source_snippets: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)

    @classmethod
    def from_values(
        cls,
        *,
        name: str,
        offer_type: str,
        audience: str = "",
        format: str = "",
    ) -> "ServiceOffer":
        return cls(
            id=service_offer_id_for_values(name or "[НУЖНО УТОЧНИТЬ]", offer_type or "educational_product"),
            name=name or "[НУЖНО УТОЧНИТЬ]",
            offer_type=offer_type or "educational_product",
            audience=audience,
            format=format,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceOffer":
        values = dict(data)
        payload: Dict[str, Any] = {}
        list_fields = {"requirements", "materials_needed", "source_snippets", "missing_info"}
        for field_name, field_info in cls.__dataclass_fields__.items():
            if field_name not in values:
                continue
            value = values[field_name]
            if field_name in list_fields:
                value = _coerce_list(value)
            if value is None and field_info.default is not MISSING:
                continue
            payload[field_name] = value
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DonorCampaign:
    id: str
    name: str = "[НУЖНО УТОЧНИТЬ]"
    campaign_type: str = "impact_digest"
    segment: str = ""
    goal: str = ""
    audience_description: str = ""
    status: str = "needs_review"
    owner: str = ""
    message_channel: str = ""
    key_message: str = ""
    impact_points: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    source_snippets: List[str] = field(default_factory=list)
    notes: str = ""
    review_state: str = "needs_review"
    next_action: str = "Проверить кампанию человеком"

    @classmethod
    def from_values(
        cls,
        *,
        name: str,
        campaign_type: str,
        segment: str,
        goal: str = "",
    ) -> "DonorCampaign":
        safe_name = name or "[НУЖНО УТОЧНИТЬ]"
        safe_type = campaign_type or "impact_digest"
        safe_segment = segment or ""
        return cls(
            id=donor_campaign_id_for_values(safe_name, safe_type, safe_segment),
            name=safe_name,
            campaign_type=safe_type,
            segment=safe_segment,
            goal=goal,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DonorCampaign":
        values = dict(data)
        payload: Dict[str, Any] = {}
        list_fields = {"impact_points", "risk_flags", "missing_info", "source_snippets"}
        for field_name, field_info in cls.__dataclass_fields__.items():
            if field_name not in values:
                continue
            value = values[field_name]
            if field_name in list_fields:
                value = _coerce_list(value)
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
    id: str = ""
    status: str = ""

    @classmethod
    def today(cls, *, action: str, entity_id: str, details: str = "") -> "ActivityLogEntry":
        timestamp = date.today().isoformat()
        return cls(
            timestamp=timestamp,
            action=action,
            entity_id=entity_id,
            details=details,
            id=activity_id_for_values(timestamp, action, entity_id, details),
        )

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
        entry = cls(**payload)
        if not entry.id:
            entry.id = activity_id_for_values(entry.timestamp, entry.action, entry.entity_id, entry.details)
        return entry

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
