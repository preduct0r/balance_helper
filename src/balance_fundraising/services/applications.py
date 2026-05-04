from __future__ import annotations

from datetime import date
from typing import Dict

from balance_fundraising.domain import ActivityLogEntry, Application

APPLICATION_STATUS_LABELS = {
    "preparing": "Готовим заявку",
    "ready_for_review": "Готово к ручной проверке",
    "submitted_by_human": "Человек уже подал заявку",
    "waiting_response": "Ждем ответ",
    "accepted": "Принято",
    "rejected": "Отклонено",
    "reporting_needed": "Нужен отчет",
    "recheck_later": "Проверить позже",
}

NEXT_ACTION_BY_STATUS = {
    "preparing": "Подготовить заявку",
    "ready_for_review": "Проверить заявку человеком",
    "submitted_by_human": "Ждать ответ или зафиксировать срок ответа",
    "waiting_response": "Проверить ответ по сроку",
    "accepted": "Зафиксировать условия и отчетность",
    "rejected": "Записать причину отказа",
    "reporting_needed": "Подготовить отчет",
    "recheck_later": "Проверить повторное окно",
}


def application_status_label(status: str) -> str:
    return APPLICATION_STATUS_LABELS.get(status, status)


def create_application_for_opportunity(store, opportunity_id: str) -> Application:
    for application in store.list_applications():
        if application.opportunity_id == opportunity_id:
            return application
    application = Application.from_opportunity(opportunity_id)
    application.status_updated_at = date.today().isoformat()
    store.upsert_application(application)
    store.add_activity(ActivityLogEntry.today(action="application_create", entity_id=application.id, details=opportunity_id))
    return application


def update_application_status(store, application_id: str, status: str, **fields: str) -> Application:
    payload: Dict[str, object] = {
        "status": status,
        "next_action": NEXT_ACTION_BY_STATUS.get(status, "Проверить следующий шаг"),
        "status_updated_at": date.today().isoformat(),
    }
    for key in ["owner", "submitted_by"]:
        if key in fields:
            payload[key] = fields[key].strip()
    application = store.update_application_fields(application_id, payload)
    store.add_activity(ActivityLogEntry.today(action="application_status", entity_id=application.id, details=status))
    return application


def update_application_dates(store, application_id: str, **fields: str) -> Application:
    payload = {key: value.strip() for key, value in fields.items() if key in {"submitted_at", "response_due_at", "reporting_due_at", "recheck_at"}}
    application = store.update_application_fields(application_id, payload)
    store.add_activity(ActivityLogEntry.today(action="application_dates", entity_id=application.id, details="updated"))
    return application


def update_application_note(store, application_id: str, notes: str) -> Application:
    application = store.update_application_fields(application_id, {"notes": notes.strip()})
    store.add_activity(ActivityLogEntry.today(action="application_note", entity_id=application.id, details="updated"))
    return application
