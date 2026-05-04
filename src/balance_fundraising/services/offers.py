from __future__ import annotations

from typing import Iterable, List

from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, ServiceOffer

OFFER_TYPES = {
    "corporate_lecture": "Корпоративная лекция",
    "wellbeing_workshop": "Wellbeing workshop",
    "psychologist_internship": "Стажировка психологов",
    "educational_product": "Образовательный продукт",
}

OFFER_STATUSES = {
    "needs_review": "Нужно проверить",
    "drafting": "Готовим описание",
    "ready_for_review": "Готово к ручной проверке",
    "approved": "Проверено",
    "paused": "На паузе",
    "archived": "В архиве",
}


def offer_type_label(offer_type: str) -> str:
    return OFFER_TYPES.get(offer_type, offer_type)


def offer_status_label(status: str) -> str:
    return OFFER_STATUSES.get(status, status)


def create_service_offer(
    store,
    *,
    name: str,
    offer_type: str,
    audience: str = "",
    format: str = "",
    value_proposition: str = "",
) -> ServiceOffer:
    offer = ServiceOffer.from_values(name=name, offer_type=offer_type, audience=audience, format=format)
    offer.value_proposition = value_proposition.strip()
    build_offer_readiness(offer)
    store.upsert_service_offer(offer)
    store.add_activity(ActivityLogEntry.today(action="offer_add", entity_id=offer.id, details=offer.offer_type))
    return offer


def update_service_offer_status(store, offer_id: str, *, status: str, review_state: str = "") -> ServiceOffer:
    fields = {}
    if status:
        fields["status"] = status
    if review_state:
        fields["review_state"] = review_state
    elif status == "approved":
        fields["review_state"] = "approved"
    offer = store.update_service_offer_fields(offer_id, fields)
    build_offer_readiness(offer)
    store.upsert_service_offer(offer)
    store.add_activity(ActivityLogEntry.today(action="offer_status", entity_id=offer.id, details=f"{offer.status} / {offer.review_state}"))
    return offer


def update_service_offer_owner(store, offer_id: str, owner: str) -> ServiceOffer:
    offer = store.update_service_offer_fields(offer_id, {"owner": owner.strip()})
    store.add_activity(ActivityLogEntry.today(action="offer_owner", entity_id=offer.id, details=offer.owner))
    return offer


def update_service_offer_note(store, offer_id: str, notes: str) -> ServiceOffer:
    offer = store.update_service_offer_fields(offer_id, {"notes": notes.strip()})
    store.add_activity(ActivityLogEntry.today(action="offer_note", entity_id=offer.id, details="updated"))
    return offer


def update_service_offer_details(
    store,
    offer_id: str,
    *,
    audience: str = "",
    format: str = "",
    value_proposition: str = "",
    requirements: Iterable[str] = (),
    materials_needed: Iterable[str] = (),
    source_snippets: Iterable[str] = (),
    missing_info: Iterable[str] = (),
) -> ServiceOffer:
    offer = store.update_service_offer_fields(
        offer_id,
        {
            "audience": audience.strip(),
            "format": format.strip(),
            "value_proposition": value_proposition.strip(),
            "requirements": _clean_list(requirements),
            "materials_needed": _clean_list(materials_needed),
            "source_snippets": _clean_list(source_snippets),
            "missing_info": _clean_list(missing_info),
        },
    )
    build_offer_readiness(offer)
    store.upsert_service_offer(offer)
    store.add_activity(ActivityLogEntry.today(action="offer_update", entity_id=offer.id, details="details"))
    return offer


def build_offer_readiness(offer: ServiceOffer) -> bool:
    missing = list(offer.missing_info)
    if not offer.audience:
        missing.append("Уточнить аудиторию")
    if not offer.format:
        missing.append("Уточнить формат")
    if not offer.value_proposition:
        missing.append("Уточнить ценность услуги")
    if not offer.materials_needed:
        missing.append("Уточнить материалы")
    missing.append("Уточнить цену")
    missing.append("Уточнить обещания результата")
    offer.missing_info = _dedupe(missing)
    return not offer.missing_info and is_offer_approved(offer)


def build_offer_description(offer: ServiceOffer, fund_wiki: Iterable[FundWikiEntry]) -> str:
    wiki = {entry.key: entry.value for entry in fund_wiki if entry.review_state == "approved" and entry.value}
    mission = wiki.get("mission", "[НУЖНО УТОЧНИТЬ]")
    programs = wiki.get("programs", "[НУЖНО УТОЧНИТЬ]")
    value = offer.value_proposition or "[НУЖНО УТОЧНИТЬ]"
    audience = offer.audience or "[НУЖНО УТОЧНИТЬ]"
    format_text = offer.format or "[НУЖНО УТОЧНИТЬ]"
    requirements = "; ".join(offer.requirements) if offer.requirements else "[НУЖНО УТОЧНИТЬ]"
    materials = "; ".join(offer.materials_needed) if offer.materials_needed else "[НУЖНО УТОЧНИТЬ]"
    gaps = "; ".join(offer.missing_info) if offer.missing_info else "[НУЖНО УТОЧНИТЬ]"
    return "\n".join(
        [
            "Описание услуги",
            "Нужна ручная проверка перед внешним использованием.",
            f"Название: {offer.name}",
            f"Тип: {offer_type_label(offer.offer_type)}",
            f"Аудитория: {audience}",
            f"Формат: {format_text}",
            f"Ценность: {value}",
            f"Требования: {requirements}",
            f"Материалы: {materials}",
            f"Миссия фонда: {mission}",
            f"Программы фонда: {programs}",
            f"Пробелы: {gaps}",
            "Цена: [НУЖНО УТОЧНИТЬ]",
            "Гарантии результата: [НУЖНО УТОЧНИТЬ]",
        ]
    )


def approved_service_offers(offers: Iterable[ServiceOffer]) -> List[ServiceOffer]:
    return [offer for offer in offers if is_offer_approved(offer)]


def is_offer_approved(offer: ServiceOffer) -> bool:
    return offer.review_state == "approved" or offer.status == "approved"


def _clean_list(values: Iterable[str]) -> List[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _dedupe(values: Iterable[str]) -> List[str]:
    deduped = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
