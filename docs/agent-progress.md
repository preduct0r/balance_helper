# Agent Progress

## 2026-04-26

- Initialized the project harness for a platform/application fundraising MVP.
- Chosen architecture: layered Python package with local JSON store for tests and Google Sheets as the production adapter.
- External calls are kept behind clients and must be mocked in tests.
- Implemented domain models, local JSON store, Google Sheets adapter, Yandex LLM helpers, Yandex Search client, text/JSON extraction, discovery/analysis/checklist/draft/digest services, CLI, and Telegram command handlers.
- Verified with `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `PYTHONPATH=src python3 scripts/dev_check.py`; both pass with 18 tests.
- Next safe step: install dependencies in a virtualenv and run a real smoke test against Yandex credentials or a real Google Sheet.

## 2026-05-04

- Added `docs/ROADMAP.md` so future agents understand the original fundraising problem and the broader multi-agent roadmap beyond the MVP.
- Linked the roadmap from `AGENTS.md`, `README.md`, and `docs/FUNDRAISING_DOMAIN.md`.
- Added a `system-roadmap` feature-list entry and harness tests for roadmap links/content.
- Added `docs/USAGE.md` as the detailed operator-facing usage guide.
- Updated `AGENTS.md` and `docs/QUALITY.md` to require keeping `docs/USAGE.md` current when service usage changes.
- Added `docs/UI_STRATEGY.md` for non-IT operator UX direction and linked it from roadmap, README, AGENTS, and quality rules.
- Added store backend selection, `doctor`, and an offline operator smoke workflow plan for the first non-IT workflow.
- Added first local server-rendered web UI plan: dashboard, opportunity list, detail, checklist, draft, and heuristic analysis.
