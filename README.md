# Balance Fundraising

MVP agent for the charity fund "Равновесие". The system helps a fundraiser find NKO platforms, extract application requirements, track deadlines, and draft application materials. It never sends applications, emails, or Telegram messages to external partners without human review.

## What It Does

- Keeps a fundraising pipeline in Google Sheets or a local JSON store.
- Searches Russian-language NKO opportunities through Yandex Search API.
- Fetches pages and documents, extracts readable text, and asks Yandex LLM for structured JSON.
- Generates checklists and draft application text from the approved `FundWiki` only.
- Provides CLI commands, Telegram command handlers, and a local web workspace for daily work.

## System Roadmap

The MVP is the first slice of a broader fundraising operating system for the fund. The full roadmap is kept in `docs/ROADMAP.md`; it covers the opportunity radar, fund passport, application/reporting agent, B2B agent, private donor agent, blogger agent, events and merch, and paid services.

The primary operator may be far from IT, so UI evolution is tracked separately in `docs/UI_STRATEGY.md`. The intended interface is a calm fundraising workspace with dashboards, review queues, opportunity cards, checklists, and editable drafts, not a technical control panel.

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=src python -m balance_fundraising.cli init-store
PYTHONPATH=src python -m balance_fundraising.cli digest
PYTHONPATH=src python -m balance_fundraising.cli doctor
PYTHONPATH=src python -m balance_fundraising.cli seed-demo
PYTHONPATH=src python -m balance_fundraising.cli web
PYTHONPATH=src python scripts/dev_check.py
```

The default store is `data/local_store.json`. Override it with:

```bash
export BALANCE_STORE_PATH=/path/to/store.json
export BALANCE_STORE_BACKEND=local
```

For detailed operator-facing usage instructions, see `docs/USAGE.md`.

## Environment Variables

- `YANDEX_API_KEY`: API key for Yandex Foundation Models and Search API.
- `YANDEX_FOLDER_ID`: Yandex Cloud folder id.
- `YANDEX_LLM_MODEL_URI`: optional model URI or model path. Defaults to `yandexgpt/latest`.
- `YANDEX_SEARCH_ENDPOINT`: optional override for the search endpoint.
- `BALANCE_STORE_BACKEND`: `local` or `google`. Defaults to `local`.
- `BALANCE_STORE_PATH`: optional local JSON store path.
- `GOOGLE_SHEET_ID`: Google Sheet id for the production store.
- `GOOGLE_SERVICE_ACCOUNT_FILE`: service account JSON file for Google Sheets.
- `TELEGRAM_BOT_TOKEN`: token for running the Telegram bot.
- `BALANCE_WEB_HOST`: optional local web host. Defaults to `127.0.0.1`.
- `BALANCE_WEB_PORT`: optional local web port. Defaults to `8080`.

## CLI

```bash
PYTHONPATH=src python -m balance_fundraising.cli init-store
PYTHONPATH=src python -m balance_fundraising.cli doctor
PYTHONPATH=src python -m balance_fundraising.cli discover
PYTHONPATH=src python -m balance_fundraising.cli add-link https://example.org/opportunity
PYTHONPATH=src python -m balance_fundraising.cli analyze <opportunity_id>
PYTHONPATH=src python -m balance_fundraising.cli checklist <opportunity_id>
PYTHONPATH=src python -m balance_fundraising.cli draft <opportunity_id>
PYTHONPATH=src python -m balance_fundraising.cli digest
PYTHONPATH=src python -m balance_fundraising.cli bot
PYTHONPATH=src python -m balance_fundraising.cli seed-demo
PYTHONPATH=src python -m balance_fundraising.cli web
PYTHONPATH=src python -m balance_fundraising.cli web --host 127.0.0.1 --port 8080
```

Use `--store-backend local|google` before the command to choose storage for that run.

`analyze` can run without an LLM in deterministic heuristic mode. Set `--use-llm` to call Yandex LLM.

## Telegram Commands

- `/digest`
- `/add_link <url>`
- `/checklist <id>`
- `/draft <id>`
- `/status <id> <status>`

The current bot adapter exposes testable command handlers and an optional polling runner when `python-telegram-bot` is installed.

## Local Web UI

Run:

```bash
PYTHONPATH=src python -m balance_fundraising.cli web
```

Open `http://127.0.0.1:8080`. The web UI is local-only and shows the same operator workflow as CLI: dashboard, review queue, opportunity list, FundWiki passport, opportunity detail, checklist, draft, and local heuristic analysis. In the opportunity card, an operator can update status, review state, owner, notes, checklist progress, and application readiness without sending anything outside the service.

Use `seed-demo` in local mode to create a training dataset for a non-IT operator. It adds demo opportunities only; it does not call Yandex, Google, Telegram, or partner services.

## Human Review Boundary

All opportunities are created as reviewable records. Drafts may contain `[НУЖНО УТОЧНИТЬ]` for missing facts. A human must approve every generated external text and every meaningful status change.

## Development Harness

Read `AGENTS.md` before coding. Use `docs/ROADMAP.md` for long-term direction, `docs/UI_STRATEGY.md` for user-facing interface direction, `docs/feature-list.json` for acceptance criteria, and `docs/agent-progress.md` for continuity between sessions.
