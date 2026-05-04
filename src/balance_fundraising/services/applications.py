from __future__ import annotations

from datetime import date
from typing import Dict

from balance_fundraising.domain import ActivityLogEntry, Application
from balance_fundraising.services.structured_logging import log_event

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

REPORTING_STATE_LABELS = {
    "not_started": "Отчет не начат",
    "prepared_by_human": "Отчет подготовлен человеком",
}


def application_status_label(status: str) -> str:
    return APPLICATION_STATUS_LABELS.get(status, status)


def reporting_state_label(state: str) -> str:
    return REPORTING_STATE_LABELS.get(state, state)


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
    log_event("application.status", "Application status updated", entity_type="application", entity_id=application.id, status=status)
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


def update_application_response(store, application_id: str, *, status: str, response_summary: str) -> Application:
    payload: Dict[str, object] = {
        "status": status,
        "response_summary": response_summary.strip(),
        "next_action": NEXT_ACTION_BY_STATUS.get(status, "Проверить следующий шаг"),
        "status_updated_at": date.today().isoformat(),
    }
    application = store.update_application_fields(application_id, payload)
    store.add_activity(ActivityLogEntry.today(action="application_response", entity_id=application.id, details=status))
    return application


def update_application_reporting(
    store,
    application_id: str,
    *,
    reporting_state: str,
    reporting_done_at: str = "",
    notes: str = "",
) -> Application:
    payload: Dict[str, object] = {
        "reporting_state": reporting_state.strip() or "not_started",
        "status_updated_at": date.today().isoformat(),
    }
    if reporting_done_at:
        payload["reporting_done_at"] = reporting_done_at.strip()
    if notes:
        payload["notes"] = notes.strip()
    if payload["reporting_state"] == "prepared_by_human":
        payload["next_action"] = "Проверить отчетность человеком"
    application = store.update_application_fields(application_id, payload)
    store.add_activity(ActivityLogEntry.today(action="application_reporting", entity_id=application.id, details=str(payload["reporting_state"])))
    return application


def build_reporting_checklist(application: Application, opportunity) -> str:
    lines = ["Отчетность:"]
    if opportunity.reporting_requirements:
        lines.extend(f"- {item}" for item in opportunity.reporting_requirements)
    else:
        lines.append("- [НУЖНО УТОЧНИТЬ] Требования к отчету")
    lines.append(f"- Срок отчета: {application.reporting_due_at or '[НУЖНО УТОЧНИТЬ] Срок отчета'}")
    lines.append(f"- Ответственный: {application.owner or '[НУЖНО УТОЧНИТЬ] Ответственный'}")
    if application.reporting_state == "prepared_by_human":
        lines.append("- Отчет подготовлен человеком")
    else:
        lines.append("- Отчет еще не отмечен как подготовленный человеком")
    return "\n".join(lines)


def update_feedback_status(store, activity_id: str, status: str) -> ActivityLogEntry:
    entry = store.update_activity_fields(activity_id, {"status": status.strip() or "new"})
    store.add_activity(ActivityLogEntry.today(action="feedback_status", entity_id=entry.id, details=entry.status))
    return entry
