from __future__ import annotations

from balance_fundraising.domain import ActivityLogEntry, Opportunity


def seed_demo_store(store) -> int:
    opportunities = [
        _opportunity(
            "https://dobro.mail.ru/funds/register",
            "VK Добро",
            "platform",
            None,
            ["Благотворительный фонд", "Публичная информация о фонде"],
            ["Устав фонда", "Отчетность фонда", "Рекомендательные письма"],
            ["Уточнить актуальные требования к верификации"],
            0.82,
        ),
        _opportunity(
            "https://sbervmeste.ru/",
            "СберВместе",
            "platform",
            "2026-04-12",
            ["НКО с публичной отчетностью"],
            ["Устав фонда", "Отчетность фонда"],
            ["Прошедший дедлайн, проверить новое окно подачи"],
            0.78,
            next_action="Проверить новое окно подачи позже",
        ),
        _opportunity(
            "https://example.org/bank-roundup",
            "Программа округления банка",
            "bank_application",
            None,
            ["НКО с подтвержденными реквизитами"],
            ["Реквизиты фонда", "Публичный отчет"],
            ["Найти контакт CSR/ESG команды"],
            0.55,
        ),
        _opportunity(
            "https://example.org/mental-health-grant",
            "Грант для НКО в сфере психического здоровья",
            "grant",
            "2026-06-01",
            ["Проекты психологической поддержки", "Опыт работы с 2020 года"],
            ["Описание проекта", "Бюджет", "Отчетность фонда"],
            ["Нужны свежие impact-показатели"],
            0.72,
        ),
        _opportunity(
            "https://example.org/charity-market",
            "Благотворительный маркет НКО",
            "event",
            "2026-05-20",
            ["НКО с мерчем или информационным стендом"],
            ["Заявка участника", "Описание мерча", "Список волонтеров"],
            ["Посчитать экономику участия"],
            0.64,
        ),
    ]
    for opportunity in opportunities:
        store.upsert_opportunity(opportunity)
        store.add_activity(ActivityLogEntry.today(action="seed_demo", entity_id=opportunity.id, details=opportunity.name))
    return len(opportunities)


def _opportunity(
    url: str,
    name: str,
    kind: str,
    deadline: str | None,
    eligibility: list[str],
    documents: list[str],
    missing_info: list[str],
    confidence: float,
    *,
    next_action: str = "Проверить и подготовить заявку",
) -> Opportunity:
    opportunity = Opportunity.from_url(url)
    opportunity.name = name
    opportunity.organization = name
    opportunity.type = kind
    opportunity.deadline = deadline
    opportunity.eligibility = eligibility
    opportunity.required_documents = documents
    opportunity.missing_info = missing_info
    opportunity.confidence = confidence
    opportunity.status = "needs_review"
    opportunity.review_state = "needs_review"
    opportunity.readiness_state = "not_started"
    opportunity.next_action = next_action
    opportunity.source_snippets = ["Демо-запись для обучения оператора без внешних отправок."]
    return opportunity
