# Testing

Testing is part of feature development, not a cleanup step.

## Commands

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/dev_check.py
```

## Strategy

- Unit tests cover pure parsing, request body construction, checklist generation, drafts, and digest ordering.
- Integration-style tests use `LocalJsonStore` only.
- External Yandex, Google, Telegram, and page-fetch calls are mocked or replaced with fixtures.
- Roadmap features are developed local/demo/mock-first until final real-world validation.
- Fixtures live in `tests/fixtures`.

## Acceptance

- Invalid LLM JSON is rejected.
- Missing fields are marked with defaults or `[НУЖНО УТОЧНИТЬ]`.
- Drafts use only `FundWiki`.
- Digest output is deterministic when a fixed date is passed.
- Harness docs remain internally linked and feature JSON remains valid.
