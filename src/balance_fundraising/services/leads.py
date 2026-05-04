from __future__ import annotations

from balance_fundraising.domain import ActivityLogEntry, FundraisingLead

LEAD_CATEGORIES = {
    "b2b": "Бизнес",
    "paid_service": "Платные услуги",
    "event": "Мероприятия и мерч",
    "blogger": "Блогеры",
    "donor_campaign": "Частные доноры",
}

LEAD_STATUSES = {
    "needs_review": "Нужно проверить",
    "contact_planned": "Запланировать контакт",
    "drafting": "Готовим черновик",
    "waiting_response": "Ждём ответ",
    "accepted": "Подходит",
    "rejected": "Не подходит",
    "recheck_later": "Проверить позже",
}


def lead_category_label(category: str) -> str:
    return LEAD_CATEGORIES.get(category, category)


def lead_status_label(status: str) -> str:
    return LEAD_STATUSES.get(status, status)


def create_lead(
    store,
    *,
    category: str,
    name: str,
    organization: str = "",
    url: str = "",
    description: str = "",
) -> FundraisingLead:
    lead = FundraisingLead.from_values(
        category=category,
        name=name,
        organization=organization,
        url=url,
        description=description,
    )
    store.upsert_lead(lead)
    store.add_activity(ActivityLogEntry.today(action="lead_add", entity_id=lead.id, details=lead.category))
    return lead


def update_lead_status(store, lead_id: str, *, status: str, review_state: str = "") -> FundraisingLead:
    fields = {}
    if status:
        fields["status"] = status
    if review_state:
        fields["review_state"] = review_state
    lead = store.update_lead_fields(lead_id, fields)
    store.add_activity(ActivityLogEntry.today(action="lead_status", entity_id=lead.id, details=f"{lead.status} / {lead.review_state}"))
    return lead


def update_lead_owner(store, lead_id: str, owner: str) -> FundraisingLead:
    lead = store.update_lead_fields(lead_id, {"owner": owner.strip()})
    store.add_activity(ActivityLogEntry.today(action="lead_owner", entity_id=lead.id, details=lead.owner))
    return lead


def update_lead_note(store, lead_id: str, notes: str) -> FundraisingLead:
    lead = store.update_lead_fields(lead_id, {"notes": notes.strip()})
    store.add_activity(ActivityLogEntry.today(action="lead_note", entity_id=lead.id, details="updated"))
    return lead
