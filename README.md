# Balance Fundraising

MVP agent for the charity fund "Равновесие". The system helps a fundraiser find NKO platforms, extract application requirements, track deadlines, and draft application materials. It never sends applications, emails, or Telegram messages to external partners without human review.

## What It Does

- Keeps a fundraising pipeline in Google Sheets or a local JSON store.
- Searches Russian-language NKO opportunities through Yandex Search API.
- Fetches pages and documents, extracts readable text, and asks Yandex LLM for structured JSON.
- Generates checklists and draft application text from the approved `FundWiki` only.
- Provides CLI commands and Telegram command handlers for daily work.

## System Roadmap

The MVP is the first slice of a broader fundraising operating system for the fund. The full roadmap is kept in `docs/ROADMAP.md`; it covers the opportunity radar, fund passport, application/reporting agent, B2B agent, private donor agent, blogger agent, events and merch, and paid services.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=src python -m balance_fundraising.cli init-store
PYTHONPATH=src python -m balance_fundraising.cli digest
PYTHONPATH=src python scripts/dev_check.py
```

The default store is `data/local_store.json`. Override it with:

```bash
export BALANCE_STORE_PATH=/path/to/store.json
```

For detailed operator-facing usage instructions, see `docs/USAGE.md`.

## Environment Variables

- `YANDEX_API_KEY`: API key for Yandex Foundation Models and Search API.
- `YANDEX_FOLDER_ID`: Yandex Cloud folder id.
- `YANDEX_LLM_MODEL_URI`: optional model URI or model path. Defaults to `yandexgpt/latest`.
- `YANDEX_SEARCH_ENDPOINT`: optional override for the search endpoint.
- `BALANCE_STORE_PATH`: optional local JSON store path.
- `GOOGLE_SHEET_ID`: Google Sheet id for the production store.
- `GOOGLE_SERVICE_ACCOUNT_FILE`: service account JSON file for Google Sheets.
- `TELEGRAM_BOT_TOKEN`: token for running the Telegram bot.

## CLI

```bash
PYTHONPATH=src python -m balance_fundraising.cli init-store
PYTHONPATH=src python -m balance_fundraising.cli discover
PYTHONPATH=src python -m balance_fundraising.cli add-link https://example.org/opportunity
PYTHONPATH=src python -m balance_fundraising.cli analyze <opportunity_id>
PYTHONPATH=src python -m balance_fundraising.cli checklist <opportunity_id>
PYTHONPATH=src python -m balance_fundraising.cli draft <opportunity_id>
PYTHONPATH=src python -m balance_fundraising.cli digest
PYTHONPATH=src python -m balance_fundraising.cli bot
```

`analyze` can run without an LLM in deterministic heuristic mode. Set `--use-llm` to call Yandex LLM.

## Telegram Commands

- `/digest`
- `/add_link <url>`
- `/checklist <id>`
- `/draft <id>`
- `/status <id> <status>`

The current bot adapter exposes testable command handlers and an optional polling runner when `python-telegram-bot` is installed.

## Human Review Boundary

All opportunities are created as reviewable records. Drafts may contain `[НУЖНО УТОЧНИТЬ]` for missing facts. A human must approve every generated external text and every meaningful status change.

## Development Harness

Read `AGENTS.md` before coding. Use `docs/ROADMAP.md` for long-term direction, `docs/feature-list.json` for acceptance criteria, and `docs/agent-progress.md` for continuity between sessions.
