from __future__ import annotations

import re
from datetime import date
from typing import Dict, Optional

from balance_fundraising.clients.page_fetcher import PageFetcher
from balance_fundraising.domain import ActivityLogEntry, Opportunity
from balance_fundraising.extractors.structured import normalize_analysis_payload, parse_analysis_json

ANALYSIS_SYSTEM_PROMPT = (
    "Ты аналитик фандрайзинга НКО. Извлекай только подтвержденные факты из текста источника. "
    "Возвращай валидный JSON по схеме. Не додумывай."
)

RUSSIAN_MONTHS = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}


class OpportunityAnalysisService:
    def __init__(self, store, *, fetcher: Optional[PageFetcher] = None, llm_client=None) -> None:
        self.store = store
        self.fetcher = fetcher or PageFetcher()
        self.llm_client = llm_client

    def analyze_opportunity(self, opportunity_id: str, *, text: Optional[str] = None, use_llm: bool = False) -> Opportunity:
        opportunity = self.store.get_opportunity(opportunity_id)
        source_text = text if text is not None else self.fetcher.fetch(opportunity.url).text
        analysis = self.analyze_text(opportunity.url, source_text, use_llm=use_llm)
        updated = Opportunity(
            id=opportunity.id,
            url=opportunity.url,
            name=analysis["name"],
            organization=analysis["organization"],
            type=analysis["type"],
            deadline=analysis["deadline"],
            status="needs_review",
            eligibility=analysis["eligibility"],
            required_documents=analysis["required_documents"],
            application_url=analysis["application_url"],
            contact=analysis["contact"],
            reporting_requirements=analysis["reporting_requirements"],
            fit_for_fund=analysis["fit_for_fund"],
            missing_info=analysis["missing_info"],
            source_snippets=analysis["source_snippets"],
            confidence=analysis["confidence"],
            next_action=_next_action(analysis["deadline"]),
            owner=opportunity.owner,
            last_checked=date.today().isoformat(),
        )
        self.store.upsert_opportunity(updated)
        self.store.add_activity(ActivityLogEntry.today(action="analyze", entity_id=updated.id, details=updated.name))
        return updated

    def analyze_text(self, url: str, text: str, *, use_llm: bool = False) -> Dict[str, object]:
        if use_llm:
            if self.llm_client is None:
                raise RuntimeError("LLM client is required when use_llm=True.")
            response = self.llm_client.complete(
                system_prompt=ANALYSIS_SYSTEM_PROMPT,
                user_prompt=build_analysis_prompt(url, text),
                temperature=0.1,
                max_tokens=2048,
            )
            return parse_analysis_json(response)
        return heuristic_analysis(url, text)


def build_analysis_prompt(url: str, text: str) -> str:
    return (
        "Источник: "
        + url
        + "\n\nИзвлеки JSON со строго такими полями: "
        + "name, organization, type, deadline, eligibility, required_documents, application_url, contact, "
        + "reporting_requirements, fit_for_fund, missing_info, source_snippets, confidence.\n"
        + "deadline верни в ISO YYYY-MM-DD, если дата найдена; иначе null. "
        + "Не добавляй пояснений вне JSON.\n\nТекст источника:\n"
        + text[:12000]
    )


def heuristic_analysis(url: str, text: str) -> Dict[str, object]:
    normalized = re.sub(r"\s+", " ", text).strip()
    deadline = _extract_deadline(normalized)
    lowered = normalized.lower()
    required_documents = []
    for keyword in ["устав", "отчет", "отчёт", "рекомендац", "регистрац", "реквизит", "презентац"]:
        if keyword in lowered:
            required_documents.append(_document_label(keyword))
    eligibility = []
    for keyword in ["нко", "фонд", "благотвор", "некоммерчес"]:
        if keyword in lowered:
            eligibility.append("Требования относятся к НКО/благотворительным фондам")
            break
    opportunity_type = "platform"
    if "грант" in lowered:
        opportunity_type = "grant"
    elif "маркет" in lowered or "ярмарк" in lowered:
        opportunity_type = "marketplace"
    elif "pro bono" in lowered or "procharity" in lowered:
        opportunity_type = "pro_bono"
    title = _first_sentence(normalized) or "[НУЖНО УТОЧНИТЬ]"
    payload = {
        "name": title[:120],
        "organization": _guess_organization(url, normalized),
        "type": opportunity_type,
        "deadline": deadline,
        "eligibility": eligibility,
        "required_documents": sorted(set(required_documents)),
        "application_url": url,
        "contact": None,
        "reporting_requirements": ["Требования к отчетности нужно проверить человеком"] if "отчет" in lowered or "отчёт" in lowered else [],
        "fit_for_fund": "unknown",
        "missing_info": ["Проверить требования и сроки человеком"],
        "source_snippets": [normalized[:260]] if normalized else [],
        "confidence": 0.35,
    }
    return normalize_analysis_payload(payload)


def _extract_deadline(text: str) -> Optional[str]:
    matches = re.findall(r"(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})", text, flags=re.IGNORECASE)
    if matches:
        day, month_name, year = matches[-1]
        return f"{year}-{RUSSIAN_MONTHS[month_name.lower()]}-{int(day):02d}"
    iso_match = re.search(r"(20\d{2})-(\d{2})-(\d{2})", text)
    if iso_match:
        return iso_match.group(0)
    return None


def _document_label(keyword: str) -> str:
    if keyword.startswith("отчет") or keyword.startswith("отчёт"):
        return "Отчетность фонда"
    if keyword.startswith("рекомендац"):
        return "Рекомендательные письма"
    if keyword.startswith("регистрац"):
        return "Регистрационные документы"
    if keyword.startswith("реквизит"):
        return "Реквизиты фонда"
    if keyword.startswith("презентац"):
        return "Презентация фонда"
    return "Устав фонда"


def _first_sentence(text: str) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return parts[0].strip() if parts else ""


def _guess_organization(url: str, text: str) -> str:
    host_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if host_match:
        return host_match.group(1)
    return "[НУЖНО УТОЧНИТЬ]"


def _next_action(deadline: Optional[str]) -> str:
    if not deadline:
        return "Проверить дедлайн и требования человеком"
    if deadline < date.today().isoformat():
        return "Дедлайн прошел: проверить следующее окно подачи"
    return "Подготовить чек-лист документов"

