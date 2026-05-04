from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List

from balance_fundraising.domain import Application, FundraisingLead, Opportunity


def build_digest(
    opportunities: Iterable[Opportunity],
    *,
    applications: Iterable[Application] | None = None,
    leads: Iterable[FundraisingLead] | None = None,
    today: date | None = None,
    horizon_days: int = 14,
) -> str:
    current = today or date.today()
    rows = sorted(opportunities, key=lambda item: (_deadline_sort_key(item.deadline), item.name))
    urgent: List[str] = []
    for opportunity in rows:
        label = _deadline_label(opportunity.deadline, current, horizon_days)
        if label:
            urgent.append(f"- {opportunity.id}: {opportunity.name} — {label}; {opportunity.next_action}")
    for application in sorted(applications or [], key=lambda item: (_deadline_sort_key(_application_sort_date(item)), item.id)):
        for line in _application_digest_lines(application, current, horizon_days):
            urgent.append(line)
    for lead in sorted(leads or [], key=lambda item: (_deadline_sort_key(_lead_sort_date(item)), item.name)):
        for line in _lead_digest_lines(lead, current, horizon_days):
            urgent.append(line)
    if not urgent:
        return "Срочных действий нет."
    return "Ближайшие действия:\n" + "\n".join(urgent[:10])


def _deadline_sort_key(deadline: str | None) -> str:
    return deadline or "9999-12-31"


def _deadline_label(deadline: str | None, today: date, horizon_days: int) -> str:
    if not deadline:
        return "дедлайн не указан"
    deadline_date = date.fromisoformat(deadline)
    if deadline_date < today:
        return f"просрочено с {deadline}"
    if deadline_date <= today + timedelta(days=horizon_days):
        return f"дедлайн {deadline}"
    return ""


def _application_sort_date(application: Application) -> str | None:
    return application.response_due_at or application.reporting_due_at or application.recheck_at


def _lead_sort_date(lead: FundraisingLead) -> str | None:
    return lead.deadline or lead.recheck_at


def _application_digest_lines(application: Application, today: date, horizon_days: int) -> List[str]:
    lines = []
    if not application.owner:
        lines.append(f"- {application.id}: нет ответственного; {application.next_action}")
    if application.response_due_at:
        label = _deadline_label(application.response_due_at, today, horizon_days)
        if label:
            prefix = "ответ просрочен" if application.response_due_at < today.isoformat() else "ответ до"
            lines.append(f"- {application.id}: {prefix} {application.response_due_at}; {application.next_action}")
    if application.reporting_due_at and application.reporting_state != "prepared_by_human":
        label = _deadline_label(application.reporting_due_at, today, horizon_days)
        if label:
            prefix = "отчет просрочен" if application.reporting_due_at < today.isoformat() else "отчет до"
            lines.append(f"- {application.id}: {prefix} {application.reporting_due_at}; {application.next_action}")
    if application.recheck_at:
        label = _deadline_label(application.recheck_at, today, horizon_days)
        if label:
            prefix = "проверка просрочена" if application.recheck_at < today.isoformat() else "проверить"
            lines.append(f"- {application.id}: {prefix} {application.recheck_at}; {application.next_action}")
    return lines


def _lead_digest_lines(lead: FundraisingLead, today: date, horizon_days: int) -> List[str]:
    lines = []
    if not lead.owner:
        lines.append(f"- {lead.id}: нет ответственного; {lead.next_action}")
    if lead.review_state != "reviewed":
        lines.append(f"- {lead.id}: нужна проверка; {lead.next_action}")
    if lead.deadline:
        label = _deadline_label(lead.deadline, today, horizon_days)
        if label:
            lines.append(f"- {lead.id}: {label}; {lead.next_action}")
    if lead.recheck_at:
        label = _deadline_label(lead.recheck_at, today, horizon_days)
        if label:
            prefix = "проверка просрочена" if lead.recheck_at < today.isoformat() else "проверить"
            lines.append(f"- {lead.id}: {prefix} {lead.recheck_at}; {lead.next_action}")
    if lead.confidence and lead.confidence < 0.4:
        lines.append(f"- {lead.id}: низкая уверенность; проверить источники")
    return lines
