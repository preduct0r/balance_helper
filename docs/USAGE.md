# Usage Guide

This guide is the operator-facing source of truth for running the MVP service. Keep it updated whenever setup, CLI commands, Telegram behavior, storage, Yandex integration, Google Sheets integration, or workflow behavior changes.

## 1. Local Setup

Create a virtual environment and install development dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Run the full local check:

```bash
PYTHONPATH=src python3 scripts/dev_check.py
```

The check runs tests and a CLI smoke test without calling real Yandex, Google, or Telegram services.

## 2. Environment Variables

Create `.env` in the project root for local secrets. `.env` is ignored by git.

Required for real Yandex LLM/Search calls:

```bash
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
```

Optional:

```bash
YANDEX_LLM_MODEL_URI=yandexgpt/latest
YANDEX_SEARCH_ENDPOINT=https://searchapi.api.cloud.yandex.net/v2/web/search
BALANCE_STORE_PATH=data/local_store.json
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
TELEGRAM_BOT_TOKEN=...
```

## 3. Local JSON Store

The MVP can run without Google Sheets using the local JSON store.

Initialize it:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli init-store
```

By default, this creates `data/local_store.json` and seeds `FundWiki` with starter facts about the fund. Override the path with:

```bash
BALANCE_STORE_PATH=/tmp/balance-store.json PYTHONPATH=src python3 -m balance_fundraising.cli init-store
```

## 4. Basic Workflow

Add a link manually:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli add-link https://example.org/opportunity
```

Analyze it with deterministic local heuristics:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli analyze <opportunity_id>
```

Analyze it with Yandex LLM:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli analyze <opportunity_id> --use-llm
```

Analyze fixture or pasted text without fetching a page:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli analyze <opportunity_id> --text-file /path/to/source.txt
```

Generate a checklist:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli checklist <opportunity_id>
```

Generate a draft:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli draft <opportunity_id>
```

Show urgent actions:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli digest
```

## 5. Discovery Workflow

Run Yandex Search discovery:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli discover
```

Discovery uses the configured Yandex Search API and creates reviewable opportunity records. Newly discovered records are not treated as approved facts. A human must review them before external action.

## 6. Telegram Bot

Set the bot token:

```bash
TELEGRAM_BOT_TOKEN=...
```

Start polling:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli bot
```

Supported commands:

- `/digest`
- `/add_link <url>`
- `/checklist <id>`
- `/draft <id>`
- `/status <id> <status>`

The bot command handlers are testable without Telegram. The polling runner requires the optional `python-telegram-bot` dependency.

## 7. Google Sheets Store

The production plan uses Google Sheets with these tabs:

- `Opportunities`
- `Applications`
- `FundWiki`
- `Documents`
- `ActivityLog`

Set:

```bash
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
```

Install the optional Google dependency when using the adapter:

```bash
python -m pip install '.[google]'
```

The local JSON store remains the required path for tests and offline development.

## 8. Human Review Boundary

The service never sends applications, emails, reports, or partner messages by itself. Generated checklists and drafts are working materials.

Before using generated text externally, a human must check:

- source URL and source snippets;
- deadline and requirements;
- missing info marked as `[НУЖНО УТОЧНИТЬ]`;
- consistency with `FundWiki`;
- absence of personal beneficiary data.

## 9. Updating This Guide

When a developer or agent changes service usage, update this file in the same change. This includes:

- new or changed CLI commands;
- new environment variables;
- changed store shape or tab names;
- changed Telegram command behavior;
- changed Yandex or Google setup;
- changed human-review workflow;
- changed troubleshooting steps.

