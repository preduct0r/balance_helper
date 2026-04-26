from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List

from balance_fundraising.domain import Opportunity


def build_digest(opportunities: Iterable[Opportunity], *, today: date | None = None, horizon_days: int = 14) -> str:
    current = today or date.today()
    rows = sorted(opportunities, key=lambda item: (_deadline_sort_key(item.deadline), item.name))
    urgent: List[str] = []
    for opportunity in rows:
        label = _deadline_label(opportunity.deadline, current, horizon_days)
        if label:
            urgent.append(f"- {opportunity.id}: {opportunity.name} — {label}; {opportunity.next_action}")
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

