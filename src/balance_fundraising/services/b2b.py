from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List

from balance_fundraising.app_defaults import DEFAULT_B2B_QUERIES
from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, FundraisingLead, ServiceOffer
from balance_fundraising.services.offers import approved_service_offers, build_offer_description


@dataclass
class B2BDiscoveryRunResult:
    queries: List[str]
    created_count: int = 0
    existing_count: int = 0
    status: str = "completed"
    error: str = ""
    leads: List[FundraisingLead] = field(default_factory=list)


class B2BDiscoveryService:
    def __init__(self, store, search_client) -> None:
        self.store = store
        self.search_client = search_client

    def discover(self, queries: Iterable[str] | None = None, *, limit_per_query: int = 10) -> B2BDiscoveryRunResult:
        query_list = [query for query in (queries or DEFAULT_B2B_QUERIES) if query]
        run = B2BDiscoveryRunResult(queries=query_list)
        for query in query_list:
            try:
                results = self.search_client.search(query, groups_on_page=limit_per_query)
            except Exception as exc:
                run.status = "failed"
                run.error = sanitize_b2b_error(str(exc))
                self.store.add_activity(ActivityLogEntry.today(action="b2b_discover_error", entity_id="b2b", details=f"{query}: {run.error}"))
                continue
            for result in results:
                lead, existed = self._lead_for_result(result.title, result.url, result.snippet)
                if existed:
                    run.existing_count += 1
                else:
                    run.created_count += 1
                lead.last_checked = date.today().isoformat()
                lead.next_action = "Проверить компанию и гипотезу партнерства"
                if result.snippet:
                    lead.source_snippets = [result.snippet]
                self.store.upsert_lead(lead)
                self.store.add_activity(ActivityLogEntry.today(action="b2b_discover", entity_id=lead.id, details=query))
                run.leads.append(lead)
        self.store.add_activity(
            ActivityLogEntry.today(
                action="b2b_discover_run",
                entity_id="b2b",
                details=(
                    f"{run.status}: queries={len(query_list)} created={run.created_count} "
                    f"existing={run.existing_count} limit={limit_per_query}"
                ),
            )
        )
        return run

    def _lead_for_result(self, title: str, url: str, snippet: str) -> tuple[FundraisingLead, bool]:
        candidate = FundraisingLead.from_values(category="b2b", name=title or "[НУЖНО УТОЧНИТЬ]", url=url, description=snippet)
        for lead in self.store.list_leads():
            same_url = bool(url and lead.url == url)
            same_name = bool(title and lead.category == "b2b" and lead.name.lower() == title.lower())
            if lead.category == "b2b" and (same_url or same_name):
                return lead, True
        return candidate, False


def analyze_b2b_lead(store, lead_id: str, *, text: str) -> FundraisingLead:
    lead = store.get_lead(lead_id)
    lowered = text.lower()
    snippets = _snippets(text)
    risk_flags = []
    missing_info = []
    fit_reasons = []
    contact = lead.contact

    if any(marker in lowered for marker in ["hr", "wellbeing", "благополуч", "сотрудник"]):
        fit_reasons.append("HR wellbeing")
    if any(marker in lowered for marker in ["обуч", "лекци", "корпоратив"]):
        fit_reasons.append("корпоративное обучение")
    if any(marker in lowered for marker in ["it", "технолог", "цифров"]):
        fit_reasons.append("IT/цифровая среда")
    if any(marker in lowered for marker in ["образован", "университет", "школ"]):
        fit_reasons.append("образование")
    if any(marker in lowered for marker in ["медицин", "здоров"]):
        fit_reasons.append("здоровье")
    if "репутац" in lowered or "риск" in lowered:
        risk_flags.append("Проверить репутацию")
    if any(marker in lowered for marker in ["форма обратной связи", "contact", "контакт", "почт"]):
        contact = "форма обратной связи или публичный контакт"

    if not contact:
        missing_info.append("Уточнить публичный контакт")
    missing_info.append("Уточнить ответственного за партнерства")
    if not fit_reasons:
        missing_info.append("Подтвердить гипотезу fit")

    lead.description = lead.description or (snippets[0] if snippets else "")
    lead.fit_for_fund = ", ".join(fit_reasons) if fit_reasons else "[НУЖНО УТОЧНИТЬ]"
    lead.contact = contact
    lead.risk_flags = risk_flags
    lead.missing_info = missing_info
    lead.source_snippets = snippets
    lead.confidence = 0.75 if fit_reasons else 0.35
    lead.next_action = "Подготовить черновик первого контакта и проверить человеком"
    lead.review_state = "needs_review"
    store.upsert_lead(lead)
    store.add_activity(ActivityLogEntry.today(action="b2b_analyze", entity_id=lead.id, details="heuristic"))
    return lead


def build_b2b_draft(
    lead: FundraisingLead,
    fund_wiki: Iterable[FundWikiEntry],
    service_offers: Iterable[ServiceOffer] = (),
) -> str:
    wiki = {entry.key: entry.value for entry in fund_wiki if entry.review_state == "approved" and entry.value}
    mission = wiki.get("mission", "[НУЖНО УТОЧНИТЬ]")
    programs = wiki.get("programs", "[НУЖНО УТОЧНИТЬ]")
    impact = wiki.get("impact", "[НУЖНО УТОЧНИТЬ]")
    evidence = "; ".join(lead.source_snippets) if lead.source_snippets else "[НУЖНО УТОЧНИТЬ]"
    contact = lead.contact or "[НУЖНО УТОЧНИТЬ]"
    fit = lead.fit_for_fund if lead.fit_for_fund != "unknown" else "[НУЖНО УТОЧНИТЬ]"
    approved_offers = approved_service_offers(service_offers)
    offer = approved_offers[0] if approved_offers else None
    offer_name = offer.name if offer else "[НУЖНО УТОЧНИТЬ]"
    offer_value = offer.value_proposition if offer and offer.value_proposition else "[НУЖНО УТОЧНИТЬ]"
    offer_description = build_offer_description(offer, fund_wiki) if offer else "[НУЖНО УТОЧНИТЬ]"
    return "\n".join(
        [
            "Черновик первого письма",
            "Нужна ручная проверка перед внешним использованием.",
            "",
            f"Кому: {lead.organization if lead.organization != '[НУЖНО УТОЧНИТЬ]' else lead.name}",
            f"Контакт: {contact}",
            "",
            "Здравствуйте!",
            f"Меня зовут [НУЖНО УТОЧНИТЬ], я представляю фонд «Равновесие». Наша миссия: {mission}",
            f"Пишем вам, потому что видим возможное пересечение с темой: {fit}. Подтверждение из источника: {evidence}",
            f"Фонд развивает программы: {programs}",
            f"Как возможный формат предлагаем обсудить: {offer_name}. Суть предложения: {offer_value}",
            "",
            "One-pager",
            f"- Организация: {lead.name}",
            f"- Гипотеза fit: {fit}",
            f"- Вариант услуги: {offer_name}",
            f"- Миссия фонда: {mission}",
            f"- Программы фонда: {programs}",
            f"- Социальный результат: {impact}",
            f"- Подтверждения: {evidence}",
            f"- Описание услуги: {offer_description}",
            "- Следующий шаг: проверить факты, контакт и формулировки человеком.",
        ]
    )


def sanitize_b2b_error(message: str) -> str:
    sanitized = message
    for key in ["YANDEX_API_KEY", "YANDEX_FOLDER_ID"]:
        value = os.getenv(key)
        if value:
            sanitized = sanitized.replace(value, "[скрыто]")
    sanitized = sanitized.replace("SECRET", "[скрыто]")
    return sanitized


def _snippets(text: str) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    return [cleaned[:300]]
