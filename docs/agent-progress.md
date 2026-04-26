# Agent Progress

## 2026-04-26

- Initialized the project harness for a platform/application fundraising MVP.
- Chosen architecture: layered Python package with local JSON store for tests and Google Sheets as the production adapter.
- External calls are kept behind clients and must be mocked in tests.
- Implemented domain models, local JSON store, Google Sheets adapter, Yandex LLM helpers, Yandex Search client, text/JSON extraction, discovery/analysis/checklist/draft/digest services, CLI, and Telegram command handlers.
- Verified with `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `PYTHONPATH=src python3 scripts/dev_check.py`; both pass with 18 tests.
- Next safe step: install dependencies in a virtualenv and run a real smoke test against Yandex credentials or a real Google Sheet.
