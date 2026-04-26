from __future__ import annotations

import json
import re
from typing import Any, Dict

REQUIRED_ANALYSIS_FIELDS = [
    "name",
    "organization",
    "type",
    "deadline",
    "eligibility",
    "required_documents",
    "application_url",
    "contact",
    "reporting_requirements",
    "fit_for_fund",
    "missing_info",
    "source_snippets",
    "confidence",
]

LIST_FIELDS = ["eligibility", "required_documents", "reporting_requirements", "missing_info", "source_snippets"]


def parse_analysis_json(response_text: str) -> Dict[str, Any]:
    text = _strip_code_fence(response_text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a JSON object.")
    return normalize_analysis_payload(payload)


def normalize_analysis_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    missing_fields = []
    for field in REQUIRED_ANALYSIS_FIELDS:
        if field not in normalized:
            missing_fields.append(field)
            normalized[field] = _default_for_field(field)
    for field in LIST_FIELDS:
        value = normalized.get(field)
        if value is None:
            normalized[field] = []
        elif isinstance(value, str):
            normalized[field] = [value]
        elif not isinstance(value, list):
            normalized[field] = [str(value)]
    if missing_fields:
        normalized["missing_info"].extend(f"Поле не найдено в ответе LLM: {field}" for field in missing_fields)
    try:
        normalized["confidence"] = float(normalized.get("confidence", 0.0))
    except (TypeError, ValueError):
        normalized["confidence"] = 0.0
    return normalized


def _default_for_field(field: str) -> Any:
    if field in LIST_FIELDS:
        return []
    if field == "confidence":
        return 0.0
    if field in {"deadline", "application_url", "contact"}:
        return None
    if field == "fit_for_fund":
        return "unknown"
    if field == "type":
        return "unknown"
    return "[НУЖНО УТОЧНИТЬ]"


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return stripped

