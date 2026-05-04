from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from balance_fundraising.domain import FundWikiEntry


@dataclass(frozen=True)
class FundWikiField:
    key: str
    label: str
    prompt: str


REQUIRED_FUND_WIKI_FIELDS = [
    FundWikiField("mission", "Миссия", "Краткая утвержденная формулировка миссии фонда."),
    FundWikiField("audience", "Кому помогает фонд", "Целевая аудитория без персональных данных."),
    FundWikiField("programs", "Программы", "Основные программы и проекты фонда."),
    FundWikiField("started", "Год начала работы", "Когда фонд начал работать."),
    FundWikiField("impact", "Социальный результат", "Проверенные impact-формулировки и показатели."),
    FundWikiField("legal_details", "Юридические данные", "Реквизиты, регистрационные и отчетные сведения."),
    FundWikiField("reports", "Отчеты", "Ссылки или описания свежих публичных отчетов."),
    FundWikiField("public_links", "Публичные ссылки", "Сайт, соцсети, страницы программ, публичная информация."),
    FundWikiField("presentation", "Презентация", "Ссылка на актуальную презентацию или one-pager."),
]

REQUIRED_FUND_WIKI_KEYS = [field.key for field in REQUIRED_FUND_WIKI_FIELDS]
FUND_WIKI_LABELS = {field.key: field.label for field in REQUIRED_FUND_WIKI_FIELDS}


def fund_wiki_by_key(entries: Iterable[FundWikiEntry]) -> dict[str, FundWikiEntry]:
    return {entry.key: entry for entry in entries if entry.key}


def missing_fund_wiki_keys(entries: Iterable[FundWikiEntry]) -> List[str]:
    by_key = fund_wiki_by_key(entries)
    missing = []
    for field in REQUIRED_FUND_WIKI_FIELDS:
        entry = by_key.get(field.key)
        if entry is None or not entry.value.strip() or entry.review_state != "approved":
            missing.append(field.key)
    return missing


def fund_wiki_label(key: str) -> str:
    return FUND_WIKI_LABELS.get(key, key)
