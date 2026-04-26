from __future__ import annotations

from typing import Iterable

from balance_fundraising.domain import FundWikiEntry, Opportunity

REQUIRED_WIKI_KEYS = ["mission", "audience", "programs", "started", "impact", "legal_details"]


def build_application_draft(opportunity: Opportunity, wiki_entries: Iterable[FundWikiEntry]) -> str:
    wiki = {entry.key: entry.value for entry in wiki_entries}
    lines = [
        f"Черновик заявки: {opportunity.name}",
        "",
        "Кратко о фонде",
        _value(wiki, "mission"),
        "",
        "Кому помогает фонд",
        _value(wiki, "audience"),
        "",
        "Программы",
        _value(wiki, "programs"),
        "",
        "Опыт работы",
        _value(wiki, "started"),
        "",
        "Почему фонд подходит для этой возможности",
        f"Площадка/программа: {opportunity.name}. Требования источника: {', '.join(opportunity.eligibility) if opportunity.eligibility else '[НУЖНО УТОЧНИТЬ]'}.",
        "",
        "Социальный результат",
        _value(wiki, "impact"),
        "",
        "Юридические и отчетные данные",
        _value(wiki, "legal_details"),
        "",
        "Что нужно уточнить перед отправкой",
    ]
    missing = sorted(set(opportunity.missing_info + [key for key in REQUIRED_WIKI_KEYS if key not in wiki]))
    lines.extend(f"- {item}" for item in missing)
    if not missing:
        lines.append("- Финальная вычитка человеком")
    return "\n".join(lines)


def _value(wiki: dict[str, str], key: str) -> str:
    return wiki.get(key, "[НУЖНО УТОЧНИТЬ]")

