from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from balance_fundraising.domain import FundWikiEntry, Opportunity
from balance_fundraising.services.fund_wiki import fund_wiki_label, missing_fund_wiki_keys

LOW_CONFIDENCE_THRESHOLD = 0.5


@dataclass(frozen=True)
class ReadinessReport:
    state: str
    ready: bool
    blockers: List[str]
    missing_wiki_keys: List[str]


def build_readiness(opportunity: Opportunity, wiki_entries: Iterable[FundWikiEntry]) -> ReadinessReport:
    blockers: List[str] = []
    if not opportunity.deadline:
        blockers.append("Уточнить дедлайн")
    if not opportunity.required_documents:
        blockers.append("Уточнить список документов")
    for document in opportunity.required_documents:
        if document and document not in opportunity.checklist_done:
            blockers.append(f"Подготовить документ: {document}")
    blockers.extend(item for item in opportunity.missing_info if item)
    missing_wiki = missing_fund_wiki_keys(wiki_entries)
    blockers.extend(f"Подтвердить факт: {fund_wiki_label(key)}" for key in missing_wiki)
    if opportunity.confidence < LOW_CONFIDENCE_THRESHOLD:
        blockers.append("Проверить низкую уверенность разбора")
    return ReadinessReport(
        state=opportunity.readiness_state,
        ready=not blockers,
        blockers=blockers,
        missing_wiki_keys=missing_wiki,
    )
