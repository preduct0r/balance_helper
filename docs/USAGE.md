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
BALANCE_STORE_BACKEND=local
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
TELEGRAM_BOT_TOKEN=...
BALANCE_WEB_HOST=127.0.0.1
BALANCE_WEB_PORT=8080
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

Choose a backend for one command:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli --store-backend local init-store
```

Or set it globally:

```bash
BALANCE_STORE_BACKEND=local
```

## 4. Diagnose Setup

Run:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli doctor
```

`doctor` checks local configuration, dependencies, `.env`, selected store backend, and optional Yandex/Google/Telegram settings. In local mode, missing external credentials are warnings, not failures.

To check Google backend configuration without making real Google calls:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli --store-backend google doctor
```

## 5. Basic Workflow

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

Run the local operator smoke workflow:

```bash
PYTHONPATH=src python3 scripts/smoke_operator_workflow.py
```

It creates a temporary local store, adds a test link, analyzes a fixture, prints a checklist, prints a draft, and prints a digest.

## 6. Local Web UI

Start the local web interface:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli web
```

Open:

```text
http://127.0.0.1:8080
```

Choose host and port:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli web --host 127.0.0.1 --port 8080
```

Or set defaults:

```bash
BALANCE_WEB_HOST=127.0.0.1
BALANCE_WEB_PORT=8080
```

The first web UI is local-only. It shows:

- dashboard with urgent actions and missing deadlines;
- opportunity list;
- opportunity detail;
- checklist;
- draft;
- local heuristic analysis from pasted text or the source URL.

It does not send applications, emails, reports, or partner messages.

## 7. Operator Recipes

### Я нашла ссылку, что делать?

1. Add it:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli add-link https://example.org/opportunity
```

2. Copy the returned `opportunity_id`.
3. Analyze it:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli analyze <opportunity_id>
```

4. Open the checklist:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli checklist <opportunity_id>
```

### Как понять, что заявка готова?

Generate the checklist and check:

- deadline is known or intentionally marked as missing;
- required documents are listed;
- missing items are resolved or assigned;
- source snippets support key facts;
- a human reviewed the draft.

### Как проверить дедлайны?

Run:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli digest
```

The digest shows overdue items, upcoming deadlines, and records with missing deadlines.

### Как получить черновик?

Run:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli draft <opportunity_id>
```

The draft uses only `FundWiki` facts. It is not ready for external use until a human edits and approves it.

### Что делать, если вижу `[НУЖНО УТОЧНИТЬ]`?

Treat it as a task, not an error. Check the source page, update `FundWiki` or the opportunity record, and regenerate the checklist or draft.

## 8. Discovery Workflow

Run Yandex Search discovery:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli discover
```

Discovery uses the configured Yandex Search API and creates reviewable opportunity records. Newly discovered records are not treated as approved facts. A human must review them before external action.

## 9. Telegram Bot

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

## 10. Google Sheets Store

The production plan uses Google Sheets with these tabs:

- `Opportunities`
- `Applications`
- `FundWiki`
- `Documents`
- `ActivityLog`

Set:

```bash
BALANCE_STORE_BACKEND=google
GOOGLE_SHEET_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
```

Install the optional Google dependency when using the adapter:

```bash
python -m pip install '.[google]'
```

The local JSON store remains the required path for tests and offline development.

## 11. Human Review Boundary

The service never sends applications, emails, reports, or partner messages by itself. Generated checklists and drafts are working materials.

Before using generated text externally, a human must check:

- source URL and source snippets;
- deadline and requirements;
- missing info marked as `[НУЖНО УТОЧНИТЬ]`;
- consistency with `FundWiki`;
- absence of personal beneficiary data.

## 12. Updating This Guide

When a developer or agent changes service usage, update this file in the same change. This includes:

- new or changed CLI commands;
- new environment variables;
- changed store shape or tab names;
- changed Telegram command behavior;
- changed Yandex or Google setup;
- changed human-review workflow;
- changed troubleshooting steps.
