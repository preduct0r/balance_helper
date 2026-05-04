from __future__ import annotations

import re
from typing import Iterable, List

from balance_fundraising.domain import ActivityLogEntry, DonorCampaign, FundWikiEntry

MISSING = "[НУЖНО УТОЧНИТЬ]"

DONOR_CAMPAIGN_TYPES = {
    "gratitude": "Благодарность",
    "impact_digest": "Impact digest",
    "reactivation": "Реактивация",
    "regular_donation_explainer": "Объяснение регулярных пожертвований",
}

DONOR_CAMPAIGN_STATUSES = {
    "needs_review": "Нужно проверить",
    "drafting": "Готовим текст",
    "ready_for_review": "Готово к ручной проверке",
    "approved": "Проверено",
    "paused": "На паузе",
    "archived": "В архиве",
}

EMAIL_RE = re.compile(r"[\w.\-+]+@[\w.\-]+\.\w+")
PHONE_RE = re.compile(r"(?:\+7|8)\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}")
FULL_NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+\b")


def donor_campaign_type_label(campaign_type: str) -> str:
    return DONOR_CAMPAIGN_TYPES.get(campaign_type, campaign_type)


def donor_campaign_status_label(status: str) -> str:
    return DONOR_CAMPAIGN_STATUSES.get(status, status)


def create_donor_campaign(
    store,
    *,
    name: str,
    campaign_type: str,
    segment: str,
    goal: str = "",
) -> DonorCampaign:
    campaign = DonorCampaign.from_values(name=name, campaign_type=campaign_type, segment=segment, goal=goal)
    build_donor_campaign_readiness(campaign)
    store.upsert_donor_campaign(campaign)
    store.add_activity(ActivityLogEntry.today(action="donor_campaign_add", entity_id=campaign.id, details=campaign.campaign_type))
    return campaign


def update_donor_campaign_status(store, campaign_id: str, *, status: str, review_state: str = "") -> DonorCampaign:
    fields = {}
    if status:
        fields["status"] = status
    if review_state:
        fields["review_state"] = review_state
    elif status == "approved":
        fields["review_state"] = "approved"
    campaign = store.update_donor_campaign_fields(campaign_id, fields)
    build_donor_campaign_readiness(campaign)
    store.upsert_donor_campaign(campaign)
    store.add_activity(
        ActivityLogEntry.today(action="donor_campaign_status", entity_id=campaign.id, details=f"{campaign.status} / {campaign.review_state}")
    )
    return campaign


def update_donor_campaign_owner(store, campaign_id: str, owner: str) -> DonorCampaign:
    campaign = store.update_donor_campaign_fields(campaign_id, {"owner": owner.strip()})
    store.add_activity(ActivityLogEntry.today(action="donor_campaign_owner", entity_id=campaign.id, details=campaign.owner))
    return campaign


def update_donor_campaign_note(store, campaign_id: str, notes: str) -> DonorCampaign:
    campaign = store.update_donor_campaign_fields(campaign_id, {"notes": notes.strip()})
    store.add_activity(ActivityLogEntry.today(action="donor_campaign_note", entity_id=campaign.id, details="updated"))
    return campaign


def update_donor_campaign_details(
    store,
    campaign_id: str,
    *,
    audience_description: str = "",
    message_channel: str = "",
    key_message: str = "",
    impact_points: Iterable[str] = (),
    risk_flags: Iterable[str] = (),
    missing_info: Iterable[str] = (),
    source_snippets: Iterable[str] = (),
) -> DonorCampaign:
    campaign = store.update_donor_campaign_fields(
        campaign_id,
        {
            "audience_description": audience_description.strip(),
            "message_channel": message_channel.strip(),
            "key_message": key_message.strip(),
            "impact_points": _clean_list(impact_points),
            "risk_flags": _clean_list(risk_flags),
            "missing_info": _clean_list(missing_info),
            "source_snippets": _clean_list(source_snippets),
        },
    )
    build_donor_campaign_readiness(campaign)
    store.upsert_donor_campaign(campaign)
    store.add_activity(ActivityLogEntry.today(action="donor_campaign_update", entity_id=campaign.id, details="details"))
    return campaign


def build_donor_campaign_readiness(campaign: DonorCampaign) -> bool:
    missing = list(campaign.missing_info)
    if not campaign.goal:
        missing.append("Уточнить цель кампании")
    if not campaign.segment:
        missing.append("Уточнить сегмент без персональных данных")
    if not campaign.message_channel:
        missing.append("Уточнить канал сообщения")
    if not campaign.impact_points:
        missing.append("Уточнить impact-факты")
    missing.append("Проверить формулировки без давления, стыда и манипуляции")

    personal_data_risks = find_personal_data_risks(
        campaign.name,
        campaign.segment,
        campaign.goal,
        campaign.audience_description,
        campaign.message_channel,
        campaign.key_message,
        "\n".join(campaign.impact_points),
        "\n".join(campaign.source_snippets),
    )
    campaign.risk_flags = _dedupe(list(campaign.risk_flags) + personal_data_risks)
    missing.extend(personal_data_risks)
    campaign.missing_info = _dedupe(missing)
    return not campaign.missing_info and campaign.review_state == "approved"


def build_donor_campaign_draft(campaign: DonorCampaign, fund_wiki: Iterable[FundWikiEntry]) -> str:
    wiki = {entry.key: entry.value for entry in fund_wiki if entry.review_state == "approved" and entry.value}
    mission = wiki.get("mission", MISSING)
    audience = wiki.get("audience", MISSING)
    programs = wiki.get("programs", MISSING)
    safety = wiki.get("safety", MISSING)
    goal = campaign.goal or MISSING
    segment = campaign.segment or MISSING
    channel = campaign.message_channel or MISSING
    key_message = campaign.key_message or MISSING
    impact = "; ".join(campaign.impact_points) if campaign.impact_points else MISSING
    evidence = "; ".join(campaign.source_snippets) if campaign.source_snippets else MISSING
    gaps = "; ".join(campaign.missing_info) if campaign.missing_info else MISSING
    risks = "; ".join(campaign.risk_flags) if campaign.risk_flags else MISSING
    body = _campaign_body(campaign.campaign_type, key_message, impact)
    return "\n".join(
        [
            "Черновик донорской кампании",
            "Нужна ручная проверка перед внешним использованием. Система ничего не отправляет.",
            "Не хранить и не вставлять сюда email, телефоны, ФИО, диагнозы или индивидуальные истории подопечных.",
            "",
            f"Кампания: {campaign.name}",
            f"Тип: {donor_campaign_type_label(campaign.campaign_type)}",
            f"Сегмент: {segment}",
            f"Цель: {goal}",
            f"Канал: {channel}",
            "",
            "Основа сообщения",
            body,
            "",
            "Факты фонда",
            f"- Миссия: {mission}",
            f"- Кому помогает фонд: {audience}",
            f"- Программы: {programs}",
            f"- Принципы безопасности: {safety}",
            f"- Impact-факты кампании: {impact}",
            f"- Подтверждения: {evidence}",
            "",
            "Проверить перед использованием",
            f"- Пробелы: {gaps}",
            f"- Риски: {risks}",
            "- Убедиться, что текст не давит, не стыдит и не обещает гарантированный результат.",
            "- Убедиться, что все данные о донорах остаются вне сервиса.",
        ]
    )


def find_personal_data_risks(*values: str) -> List[str]:
    text = "\n".join(value for value in values if value)
    risks = []
    if EMAIL_RE.search(text):
        risks.append("Найден email: не хранить персональные контакты доноров")
    if PHONE_RE.search(text):
        risks.append("Найден телефон: не хранить персональные контакты доноров")
    if FULL_NAME_RE.search(text):
        risks.append("Найдены ФИО-похожие данные: хранить только сегменты, не списки людей")
    return _dedupe(risks)


def _campaign_body(campaign_type: str, key_message: str, impact: str) -> str:
    if campaign_type == "gratitude":
        return "\n".join(
            [
                "Здравствуйте!",
                "Спасибо, что поддерживаете фонд «Равновесие». Ваша регулярность помогает нам планировать безопасную помощь.",
                f"Главная мысль: {key_message}",
                f"Что удалось сделать: {impact}",
            ]
        )
    if campaign_type == "reactivation":
        return "\n".join(
            [
                "Здравствуйте!",
                "Мы бережно напоминаем о возможности вернуться к поддержке фонда в том темпе, который вам комфортен.",
                f"Главная мысль: {key_message}",
                f"Что важно показать: {impact}",
            ]
        )
    if campaign_type == "regular_donation_explainer":
        return "\n".join(
            [
                "Здравствуйте!",
                "Регулярное пожертвование помогает фонду планировать группы, консультации и поддержку команды заранее.",
                f"Главная мысль: {key_message}",
                f"Пример влияния регулярности: {impact}",
            ]
        )
    return "\n".join(
        [
            "Здравствуйте!",
            "Делимся спокойным дайджестом о работе фонда и о том, как поддержка превращается в устойчивые форматы помощи.",
            f"Главная мысль: {key_message}",
            f"Что показать в дайджесте: {impact}",
        ]
    )


def _clean_list(values: Iterable[str]) -> List[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _dedupe(values: Iterable[str]) -> List[str]:
    deduped = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped
