from __future__ import annotations

from typing import Iterable

from balance_fundraising.domain import FundWikiEntry, Opportunity
from balance_fundraising.services.fund_wiki import fund_wiki_label, missing_fund_wiki_keys


def build_application_draft(opportunity: Opportunity, wiki_entries: Iterable[FundWikiEntry]) -> str:
    entries = list(wiki_entries)
    wiki = {entry.key: entry.value for entry in entries}
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
        "Отчеты и публичные материалы",
        f"Отчеты: {_value(wiki, 'reports')}",
        f"Публичные ссылки: {_value(wiki, 'public_links')}",
        f"Презентация: {_value(wiki, 'presentation')}",
        "",
        "Что нужно уточнить перед отправкой",
    ]
    wiki_gaps = [fund_wiki_label(key) for key in missing_fund_wiki_keys(entries)]
    missing = sorted(set(opportunity.missing_info + wiki_gaps))
    lines.extend(f"- {item}" for item in missing)
    if not missing:
        lines.append("- Финальная вычитка человеком")
    return "\n".join(lines)


def _value(wiki: dict[str, str], key: str) -> str:
    return wiki.get(key, "[НУЖНО УТОЧНИТЬ]")
