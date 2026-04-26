from __future__ import annotations

from balance_fundraising.domain import Opportunity


def build_checklist(opportunity: Opportunity) -> str:
    lines = [
        f"Чек-лист: {opportunity.name}",
        f"Статус: {opportunity.status}",
        f"Источник: {opportunity.url}",
    ]
    if opportunity.deadline:
        lines.append(f"Дедлайн: {opportunity.deadline}")
    lines.append("")
    lines.append("Требования:")
    if opportunity.eligibility:
        lines.extend(f"- {item}" for item in opportunity.eligibility)
    else:
        lines.append("- [НУЖНО УТОЧНИТЬ] Требования к участию")
    lines.append("")
    lines.append("Документы:")
    if opportunity.required_documents:
        lines.extend(f"- {item}" for item in opportunity.required_documents)
    else:
        lines.append("- [НУЖНО УТОЧНИТЬ] Список документов")
    lines.append("")
    lines.append(f"Следующее действие: {opportunity.next_action}")
    return "\n".join(lines)

