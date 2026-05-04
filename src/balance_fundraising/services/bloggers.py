from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, List

from balance_fundraising.app_defaults import DEFAULT_BLOGGER_QUERIES
from balance_fundraising.domain import ActivityLogEntry, FundWikiEntry, FundraisingLead

MISSING = "[НУЖНО УТОЧНИТЬ]"


@dataclass
class BloggerDiscoveryRunResult:
    queries: List[str]
    created_count: int = 0
    existing_count: int = 0
    status: str = "completed"
    error: str = ""
    leads: List[FundraisingLead] = field(default_factory=list)


class BloggerDiscoveryService:
    def __init__(self, store, search_client) -> None:
        self.store = store
        self.search_client = search_client

    def discover(self, queries: Iterable[str] | None = None, *, limit_per_query: int = 10) -> BloggerDiscoveryRunResult:
        query_list = [query for query in (queries or DEFAULT_BLOGGER_QUERIES) if query]
        run = BloggerDiscoveryRunResult(queries=query_list)
        for query in query_list:
            try:
                results = self.search_client.search(query, groups_on_page=limit_per_query)
            except Exception as exc:
                run.status = "failed"
                run.error = sanitize_blogger_error(str(exc))
                self.store.add_activity(
                    ActivityLogEntry.today(action="blogger_discover_error", entity_id="blogger", details=f"{query}: {run.error}")
                )
                continue
            for result in results:
                lead, existed = self._lead_for_result(result.title, result.url, result.snippet)
                run.existing_count += 1 if existed else 0
                run.created_count += 0 if existed else 1
                lead.last_checked = date.today().isoformat()
                lead.next_action = "Проверить этику, репутацию и формат коллаборации"
                if result.snippet:
                    lead.source_snippets = [result.snippet]
                self.store.upsert_lead(lead)
                self.store.add_activity(ActivityLogEntry.today(action="blogger_discover", entity_id=lead.id, details=query))
                run.leads.append(lead)
        self.store.add_activity(
            ActivityLogEntry.today(
                action="blogger_discover_run",
                entity_id="blogger",
                details=(
                    f"{run.status}: queries={len(query_list)} created={run.created_count} "
                    f"existing={run.existing_count} limit={limit_per_query}"
                ),
            )
        )
        return run

    def _lead_for_result(self, title: str, url: str, snippet: str) -> tuple[FundraisingLead, bool]:
        candidate = FundraisingLead.from_values(
            category="blogger",
            name=title or MISSING,
            url=url,
            description=snippet,
        )
        for lead in self.store.list_leads():
            same_url = bool(url and lead.url == url)
            same_name = bool(title and lead.category == "blogger" and lead.name.lower() == title.lower())
            if lead.category == "blogger" and (same_url or same_name):
                return lead, True
        return candidate, False


def create_blogger_lead(store, *, name: str, url: str = "", description: str = "") -> FundraisingLead:
    lead = FundraisingLead.from_values(
        category="blogger",
        name=name,
        url=url,
        description=description,
    )
    lead.next_action = "Проверить этику, репутацию и формат коллаборации"
    store.upsert_lead(lead)
    store.add_activity(ActivityLogEntry.today(action="blogger_add", entity_id=lead.id, details=lead.name))
    return lead


def analyze_blogger_lead(store, lead_id: str, *, text: str) -> FundraisingLead:
    lead = store.get_lead(lead_id)
    lowered = text.lower()
    snippets = _snippets(text)
    fit_reasons = []
    risk_flags = []
    missing_info = []
    contact = lead.contact

    if any(marker in lowered for marker in ["психолог", "менталь", "психическ"]):
        fit_reasons.append("ментальное здоровье")
    if any(marker in lowered for marker in ["нейро", "нейроотлич"]):
        fit_reasons.append("нейроотличия")
    if "инклюз" in lowered:
        fit_reasons.append("инклюзия")
    if any(marker in lowered for marker in ["hr", "wellbeing", "сотрудник"]):
        fit_reasons.append("HR/wellbeing")
    if any(marker in lowered for marker in ["образован", "просвещ", "лекци"]):
        fit_reasons.append("образование")
    if any(marker in lowered for marker in ["благотвор", "сбор", "нко"]):
        fit_reasons.append("благотворительная коллаборация")
    if any(marker in lowered for marker in ["форма обратной связи", "контакт", "почт", "email", "ссылка для связи"]):
        contact = "форма обратной связи или публичный контакт"
    if any(marker in lowered for marker in ["риск", "репутац", "скандал", "конфликт"]):
        risk_flags.append("Проверить репутацию")
    if any(marker in lowered for marker in ["стигм", "диагноз", "остр"]):
        risk_flags.append("Проверить этичные формулировки")

    if not contact:
        missing_info.append("Уточнить публичный контакт")
    missing_info.extend(
        [
            "Проверить согласие на любые личные истории",
            "Уточнить формат коллаборации",
            "Проверить репутационные риски",
        ]
    )
    if not fit_reasons:
        missing_info.append("Подтвердить тематический fit")

    lead.description = lead.description or (snippets[0] if snippets else "")
    lead.fit_for_fund = ", ".join(fit_reasons) if fit_reasons else MISSING
    lead.contact = contact
    lead.risk_flags = risk_flags
    lead.missing_info = missing_info
    lead.source_snippets = snippets
    lead.confidence = 0.75 if fit_reasons else 0.35
    lead.next_action = "Проверить этический чек-лист и подготовить черновик"
    lead.review_state = "needs_review"
    store.upsert_lead(lead)
    store.add_activity(ActivityLogEntry.today(action="blogger_analyze", entity_id=lead.id, details="heuristic"))
    return lead


def build_blogger_ethics_checklist(lead: FundraisingLead, fund_wiki: Iterable[FundWikiEntry]) -> str:
    wiki = {entry.key: entry.value for entry in fund_wiki if entry.review_state == "approved" and entry.value}
    mission = wiki.get("mission", MISSING)
    evidence = "; ".join(lead.source_snippets) if lead.source_snippets else MISSING
    missing_info = "; ".join(lead.missing_info) if lead.missing_info else MISSING
    risks = "; ".join(lead.risk_flags) if lead.risk_flags else MISSING
    return "\n".join(
        [
            "Этический чек-лист блогера",
            "Нужна ручная проверка перед любым внешним контактом или публикацией.",
            "",
            f"- Блогер/сообщество: {lead.name or MISSING}",
            f"- Источник: {lead.url or MISSING}",
            f"- Подтверждения: {evidence}",
            f"- Миссия фонда для сверки: {mission}",
            f"- Нет стигматизирующих формулировок: {MISSING}",
            f"- Нет давления на подопечных: {MISSING}",
            f"- Нет личных историй без отдельного согласия: {MISSING}",
            f"- Репутационные риски блогера/сообщества: {risks}",
            f"- соответствие ценностям фонда: {MISSING}",
            f"- Возможный формат: эфир, пост, сбор, амбассадорство, аукцион, мерч-дроп",
            f"- Что неизвестно: {missing_info}",
            "",
            "Границы v1: без рассылок, личных сообщений, автокомментариев, закрытого парсинга и внешних отправок.",
        ]
    )


def build_blogger_collaboration_draft(lead: FundraisingLead, fund_wiki: Iterable[FundWikiEntry]) -> str:
    wiki = {entry.key: entry.value for entry in fund_wiki if entry.review_state == "approved" and entry.value}
    mission = wiki.get("mission", MISSING)
    programs = wiki.get("programs", MISSING)
    audience = wiki.get("audience", MISSING)
    evidence = "; ".join(lead.source_snippets) if lead.source_snippets else MISSING
    fit = lead.fit_for_fund if lead.fit_for_fund != "unknown" else MISSING
    contact = lead.contact or MISSING
    return "\n".join(
        [
            "Черновик предложения коллаборации",
            "Нужна ручная проверка перед внешним использованием.",
            "",
            f"Кому: {lead.name}",
            f"Публичный контакт: {contact}",
            "",
            "Здравствуйте!",
            f"Меня зовут [НУЖНО УТОЧНИТЬ], я представляю фонд «Равновесие». Наша миссия: {mission}",
            f"Мы заметили возможное пересечение с темой: {fit}. Подтверждение из источника: {evidence}",
            f"Фонд работает для аудитории: {audience}",
            f"Программы фонда: {programs}",
            "Возможный формат для обсуждения: [НУЖНО УТОЧНИТЬ] эфир, пост, сбор, амбассадорство, аукцион или мерч-дроп.",
            "",
            "Outline формата",
            f"- Почему может подойти: {fit}",
            f"- Подтверждения: {evidence}",
            "- Этическая граница: не использовать личные истории подопечных без отдельного согласия.",
            "- Следующий шаг: проверить репутацию, тональность, факты и формат человеком.",
        ]
    )


def sanitize_blogger_error(message: str) -> str:
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
