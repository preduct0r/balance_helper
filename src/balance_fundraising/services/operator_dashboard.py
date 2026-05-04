from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List, Optional

from balance_fundraising.domain import Application, DonorCampaign, FundraisingLead, Opportunity, ServiceOffer
from balance_fundraising.services.applications import application_status_label
from balance_fundraising.services.donors import donor_campaign_status_label
from balance_fundraising.services.leads import lead_category_label, lead_status_label
from balance_fundraising.services.offers import offer_status_label


@dataclass(frozen=True)
class OperatorWorkItem:
    kind: str
    id: str
    title: str
    section: str
    url: str
    status: str
    owner: str
    date: Optional[str]
    reason: str
    next_action: str
    severity: str


def build_operator_work_items(
    opportunities: Iterable[Opportunity],
    *,
    applications: Iterable[Application] | None = None,
    leads: Iterable[FundraisingLead] | None = None,
    service_offers: Iterable[ServiceOffer] | None = None,
    donor_campaigns: Iterable[DonorCampaign] | None = None,
    today: date | None = None,
    horizon_days: int = 14,
) -> List[OperatorWorkItem]:
    current = today or date.today()
    items: List[OperatorWorkItem] = []
    for opportunity in opportunities:
        items.extend(_opportunity_items(opportunity, current, horizon_days))
    for application in applications or []:
        items.extend(_application_items(application, current, horizon_days))
    for lead in leads or []:
        items.extend(_lead_items(lead, current, horizon_days))
    for offer in service_offers or []:
        items.extend(_offer_items(offer))
    for campaign in donor_campaigns or []:
        items.extend(_donor_campaign_items(campaign))
    return sorted(items, key=_work_item_sort_key)


def section_counts(
    *,
    opportunities: Iterable[Opportunity],
    applications: Iterable[Application],
    leads: Iterable[FundraisingLead],
    service_offers: Iterable[ServiceOffer],
    donor_campaigns: Iterable[DonorCampaign],
) -> dict[str, int]:
    lead_rows = list(leads)
    return {
        "Платформы": len(list(opportunities)),
        "Заявки": len(list(applications)),
        "B2B": len([item for item in lead_rows if item.category == "b2b"]),
        "Услуги": len(list(service_offers)),
        "Мероприятия": len([item for item in lead_rows if item.category == "event"]),
        "Блогеры": len([item for item in lead_rows if item.category == "blogger"]),
        "Доноры": len(list(donor_campaigns)),
    }


def _opportunity_items(opportunity: Opportunity, today: date, horizon_days: int) -> List[OperatorWorkItem]:
    items = []
    if opportunity.status in {"accepted", "rejected"} and opportunity.review_state == "reviewed":
        return items
    label = _deadline_label(opportunity.deadline, today, horizon_days)
    if label:
        items.append(
            _item(
                kind="opportunity",
                id=opportunity.id,
                title=opportunity.name,
                section="Платформы",
                url=f"/opportunities/{opportunity.id}",
                status=opportunity.status,
                owner=opportunity.owner,
                date=opportunity.deadline,
                reason=label,
                next_action=opportunity.next_action,
                severity="urgent",
            )
        )
    if opportunity.review_state != "reviewed" or opportunity.status in {"needs_review", "discovered"}:
        items.append(
            _item(
                kind="opportunity",
                id=opportunity.id,
                title=opportunity.name,
                section="Платформы",
                url=f"/opportunities/{opportunity.id}",
                status=opportunity.status,
                owner=opportunity.owner,
                date=opportunity.deadline,
                reason="нужна проверка",
                next_action=opportunity.next_action,
                severity="review",
            )
        )
    gap_reasons = []
    if not opportunity.deadline:
        gap_reasons.append("дедлайн не указан")
    gap_reasons.extend(opportunity.missing_info)
    if opportunity.confidence and opportunity.confidence < 0.4:
        gap_reasons.append("низкая уверенность")
    if gap_reasons:
        items.append(
            _item(
                kind="opportunity",
                id=opportunity.id,
                title=opportunity.name,
                section="Платформы",
                url=f"/opportunities/{opportunity.id}",
                status=opportunity.status,
                owner=opportunity.owner,
                date=opportunity.deadline,
                reason="; ".join(gap_reasons),
                next_action=opportunity.next_action,
                severity="gap",
            )
        )
    return items


def _application_items(application: Application, today: date, horizon_days: int) -> List[OperatorWorkItem]:
    items = []
    if _needs_owner(application.status, inactive={"accepted", "rejected"}) and not application.owner:
        items.append(
            _item(
                kind="application",
                id=application.id,
                title=application.id,
                section="Заявки",
                url=f"/applications/{application.id}",
                status=application_status_label(application.status),
                owner=application.owner,
                date=_application_sort_date(application),
                reason="нет ответственного",
                next_action=application.next_action,
                severity="owner",
            )
        )
    for value, label in [
        (application.response_due_at, "срок ответа"),
        (application.reporting_due_at if application.reporting_state != "prepared_by_human" else None, "срок отчета"),
        (application.recheck_at, "проверить позже"),
    ]:
        deadline = _deadline_label(value, today, horizon_days)
        if deadline:
            items.append(
                _item(
                    kind="application",
                    id=application.id,
                    title=application.id,
                    section="Заявки",
                    url=f"/applications/{application.id}",
                    status=application_status_label(application.status),
                    owner=application.owner,
                    date=value,
                    reason=f"{label}: {deadline}",
                    next_action=application.next_action,
                    severity="urgent",
                )
            )
    return items


def _lead_items(lead: FundraisingLead, today: date, horizon_days: int) -> List[OperatorWorkItem]:
    items = []
    section = _lead_section(lead)
    url = _lead_url(lead)
    if _needs_owner(lead.status, inactive={"accepted", "rejected"}) and not lead.owner:
        items.append(_item("lead", lead.id, lead.name, section, url, lead_status_label(lead.status), lead.owner, _lead_sort_date(lead), "нет ответственного", lead.next_action, "owner"))
    if lead.review_state != "reviewed" or lead.status == "needs_review":
        items.append(_item("lead", lead.id, lead.name, section, url, lead_status_label(lead.status), lead.owner, _lead_sort_date(lead), "нужна проверка", lead.next_action, "review"))
    gap_reasons = list(lead.missing_info) + list(lead.risk_flags)
    if lead.confidence and lead.confidence < 0.4:
        gap_reasons.append("низкая уверенность")
    if gap_reasons:
        items.append(_item("lead", lead.id, lead.name, section, url, lead_status_label(lead.status), lead.owner, _lead_sort_date(lead), "; ".join(gap_reasons), lead.next_action, "gap"))
    for value, label in [(lead.deadline, "дедлайн"), (lead.recheck_at, "проверить")]:
        deadline = _deadline_label(value, today, horizon_days)
        if deadline:
            items.append(_item("lead", lead.id, lead.name, section, url, lead_status_label(lead.status), lead.owner, value, f"{label}: {deadline}", lead.next_action, "urgent"))
    return items


def _offer_items(offer: ServiceOffer) -> List[OperatorWorkItem]:
    items = []
    status = offer_status_label(offer.status)
    if _needs_owner(offer.status, inactive={"approved", "archived"}) and not offer.owner:
        items.append(_item("service_offer", offer.id, offer.name, "Услуги", f"/offers/{offer.id}", status, offer.owner, None, "нет ответственного", "Проверить услугу", "owner"))
    if offer.review_state != "approved" and offer.status != "approved":
        items.append(_item("service_offer", offer.id, offer.name, "Услуги", f"/offers/{offer.id}", status, offer.owner, None, "нужна проверка", "Проверить описание услуги", "review"))
    if offer.missing_info:
        items.append(_item("service_offer", offer.id, offer.name, "Услуги", f"/offers/{offer.id}", status, offer.owner, None, "; ".join(offer.missing_info), "Заполнить пробелы услуги", "gap"))
    return items


def _donor_campaign_items(campaign: DonorCampaign) -> List[OperatorWorkItem]:
    items = []
    status = donor_campaign_status_label(campaign.status)
    if _needs_owner(campaign.status, inactive={"approved", "archived"}) and not campaign.owner:
        items.append(_item("donor_campaign", campaign.id, campaign.name, "Доноры", f"/donors/{campaign.id}", status, campaign.owner, None, "нет ответственного", campaign.next_action, "owner"))
    if campaign.review_state != "approved" and campaign.status != "approved":
        items.append(_item("donor_campaign", campaign.id, campaign.name, "Доноры", f"/donors/{campaign.id}", status, campaign.owner, None, "нужна проверка", campaign.next_action, "review"))
    gap_reasons = list(campaign.missing_info) + list(campaign.risk_flags)
    if gap_reasons:
        items.append(_item("donor_campaign", campaign.id, campaign.name, "Доноры", f"/donors/{campaign.id}", status, campaign.owner, None, "; ".join(gap_reasons), campaign.next_action, "gap"))
    return items


def _item(
    kind: str,
    id: str,
    title: str,
    section: str,
    url: str,
    status: str,
    owner: str,
    date: Optional[str],
    reason: str,
    next_action: str,
    severity: str,
) -> OperatorWorkItem:
    return OperatorWorkItem(
        kind=kind,
        id=id,
        title=title,
        section=section,
        url=url,
        status=status,
        owner=owner,
        date=date,
        reason=reason,
        next_action=next_action,
        severity=severity,
    )


def _lead_section(lead: FundraisingLead) -> str:
    if lead.category == "b2b":
        return "B2B"
    if lead.category == "event":
        return "Мероприятия"
    if lead.category == "blogger":
        return "Блогеры"
    return lead_category_label(lead.category)


def _lead_url(lead: FundraisingLead) -> str:
    if lead.category == "b2b":
        return f"/b2b/{lead.id}"
    if lead.category == "event":
        return f"/events/{lead.id}"
    if lead.category == "blogger":
        return f"/bloggers/{lead.id}"
    return f"/leads/{lead.id}"


def _deadline_label(value: str | None, today: date, horizon_days: int) -> str:
    if not value:
        return ""
    try:
        deadline = date.fromisoformat(value)
    except ValueError:
        return "дата требует проверки"
    if deadline < today:
        return f"просрочено с {value}"
    if deadline <= today + timedelta(days=horizon_days):
        return f"дедлайн {value}"
    return ""


def _needs_owner(status: str, *, inactive: set[str]) -> bool:
    return status not in inactive


def _application_sort_date(application: Application) -> str | None:
    return application.response_due_at or application.reporting_due_at or application.recheck_at


def _lead_sort_date(lead: FundraisingLead) -> str | None:
    return lead.deadline or lead.recheck_at


def _work_item_sort_key(item: OperatorWorkItem) -> tuple[int, str, str, str, str]:
    severity_order = {"urgent": 0, "owner": 1, "review": 2, "gap": 3}
    return (severity_order.get(item.severity, 9), item.date or "9999-12-31", item.section, item.title, item.reason)
