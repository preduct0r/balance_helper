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

Run the opportunity radar with all curated queries:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli discover
```

Run the radar for one query and a smaller result count:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli discover --query "партнерство НКО банк" --limit 5
```

Use `discover --limit 5` with or without `--query` to keep early runs small.

Show application pipeline records:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli applications
```

Create an internal application record from an opportunity:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli application-create <opportunity_id>
```

Move an internal application to another stage:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli application-status <application_id> waiting_response
```

Show one application:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli application-show <application_id>
```

Update application dates:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli application-dates <application_id> --response-due 2026-05-20 --reporting-due 2026-06-20 --recheck 2026-05-30
```

Save an internal application note:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli application-note <application_id> "Ответ ждём в кабинете платформы"
```

Show contacts and future fundraising directions:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli leads
```

Add a contact or direction for the roadmap workspace:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli lead-add --category b2b --name "Компания заботы" --url https://company.example --description "HR wellbeing"
```

Move an internal lead to another safe stage:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli lead-status <lead_id> contact_planned
```

Show one lead:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli lead-show <lead_id>
```

Run B2B radar for company leads:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli b2b-radar --query "HR wellbeing партнерство НКО" --limit 5
```

Analyze a B2B lead from pasted/source text:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli b2b-analyze <lead_id> --text-file /path/to/company.txt
```

Generate a human-reviewed B2B draft:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli b2b-draft <lead_id>
```

Run the local operator smoke workflow:

```bash
PYTHONPATH=src python3 scripts/smoke_operator_workflow.py
```

It creates a temporary local store, adds a test link, analyzes a fixture, prints a checklist, prints a draft, and prints a digest.

Create a safe training dataset in the selected local store:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli seed-demo
```

`seed-demo` adds a тренировочный набор with realistic demo opportunities such as VK Добро, СберВместе, a bank roundup program, a grant, and a charity market. It does not call external services.

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
- `Радар` for curated Yandex Search discovery;
- `B2B` for company search, fit review, risk checks, and first-contact drafts;
- `Контакты и направления` for future B2B, paid services, events, bloggers, and donor campaign records;
- opportunity list;
- application list;
- application detail page with response, reporting, history, and follow-up dates;
- review queue;
- `FundWiki` / Паспорт фонда;
- "Первый прогон" validation screen;
- opportunity detail;
- checklist;
- draft;
- readiness block for "Подготовить заявку";
- safe operator actions: status, review state, owner, notes, checklist done, application readiness, internal application stage, application dates, response summary, reporting state, application notes, and first-run observation status;
- local heuristic analysis from pasted text or the source URL.

It does not send applications, emails, reports, or partner messages.

### B2B: как искать компании и готовить первый контакт

1. Open "B2B".
2. Choose a curated query or type a one-time query.
3. Keep the limit at `5` for early runs.
4. Open a company lead and paste source text if the automatic snippet is not enough.
5. Check fit, risk flags, missing info, source snippets, and public contact.
6. Read "Черновик первого письма" and "One-pager" as preparation material only.
7. Do not send the text until a human checks the company, facts, tone, and FundWiki references.

CLI equivalents are `b2b-radar`, `b2b-analyze`, and `b2b-draft`. B2B v1 does not store private employee data and does not send emails, forms, Telegram messages, or CRM tasks.

### Контакты и направления

Use this section for roadmap records that are not platform applications yet: a potential business partner, paid service idea, market, blogger, or donor campaign segment.

1. Open "Контакты и направления".
2. Add a record with category, name, optional organization, source link, and short description.
3. Open the card and assign an owner if someone should check it.
4. Update status, review state, and notes only as internal tracking.
5. Use the digest and "Проверка" queue to catch missing owners, review items, recheck dates, and upcoming deadlines.

Lead records do not send emails, create applications, or contact anyone. They are the shared workspace for future B2B, paid service, event, blogger, and donor-campaign agents.

### Радар: как искать новые площадки

1. Open "Радар".
2. Choose one curated query or leave "Все запросы".
3. Optionally type a one-time custom query.
4. Keep the limit at `5` for the first runs.
5. Click "Запустить радар".
6. Open new findings from "Новые находки" or "Проверка".

Radar only creates reviewable opportunity cards with status `discovered`. It does not analyze pages with LLM, create applications, or send anything externally. If Yandex settings are missing, the page shows a friendly warning instead of crashing.

### Web scenario for a non-IT operator

1. Open the dashboard and start with "Сегодня важно".
2. Open "Проверка" to see new findings and drafts that need a person.
3. Open an opportunity card.
4. Check "Готовность заявки" first: it shows missing documents, missing deadline, low confidence, and FundWiki gaps.
5. Open "Паспорт фонда" when the card says that reusable facts are missing.
6. Create a "Заявка" record only when the team is actually preparing this opportunity.
7. Check "Что неизвестно" and "Подтверждения".
8. Assign an owner if the next step belongs to someone.
9. Save a note when context would otherwise live in chat.
10. Mark checklist items done only after checking the real source or document.
11. Treat every draft as preparation material until a human approves it.

### Training scenario without risk

1. Run `seed-demo`.
2. Start `web`.
3. Open "Первый прогон" and read the checklist before touching real records.
4. Open "Проверка" and choose a demo opportunity.
5. Open "Паспорт фонда" and fill one missing block, for example "Социальный результат".
6. Return to the opportunity and check "Готовность заявки".
7. Create or open the "Заявка" block and move only internal stages.
8. Change readiness to "Готовим документы" or "Готово к ручной проверке" only if the remaining blockers make sense to a human.

### First real-world smoke checklist

Use this for the first пользовательский прогон with a real link:

1. Add one real opportunity link in the web UI.
2. Run analysis from pasted source text if automatic fetch is not reliable.
3. Check deadline, documents, unknowns, and source snippets.
4. Open "Паспорт фонда" and fill only facts that are already confirmed by fund materials.
5. Return to "Готовность заявки" and assign owners for every blocker.
6. Create a "Заявка" record and set the current internal stage.
7. Generate/read the draft, but do not send it externally.
8. Open "Первый прогон" and record what was confusing, missing, or excessive in the feedback form before the next development step.

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
- `FundWiki` gaps are filled in "Паспорт фонда";
- "Готовность заявки" has no blocking items, or each blocker has a named owner;
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

### мы реально подаём заявку, как вести процесс?

1. Open the opportunity in the web UI.
2. Check "Готовность заявки" and resolve or assign every blocker.
3. In the "Заявка" block, click "Создать заявку".
4. Set the internal stage to "Готовим заявку".
5. Fill owner, next known dates, and a short note with the real next step.
6. Move the stage to "Готово к ручной проверке" only after a person checks the source, documents, checklist, and draft.
7. Keep using the digest and `/applications` page to avoid losing response or reporting dates.

### ждём ответ, как вести follow-up?

1. Open `/applications` and choose the application.
2. Set the stage to "Ждем ответ".
3. Fill "Срок ответа" if the platform gave one.
4. Assign an owner.
5. Save a note with where to check the answer.
6. Watch `digest`: overdue response dates appear there before anything is sent or changed outside the service.

### получили отказ, что записать?

1. Open the application detail page.
2. In "Ответ площадки", set the result to "Отклонено".
3. Add a short response summary: reason, source, and whether recheck is possible.
4. If there may be a future window, fill "Проверить позже" and set the stage to "Проверить позже".
5. Keep the note factual; no external message is sent.

### заявку приняли, что дальше?

1. Open the application detail page.
2. In "Ответ площадки", set the result to "Принято".
3. Add response summary with conditions and where the confirmation is stored.
4. If the platform requires a report, set the stage to "Нужен отчет" and fill "Срок отчета".
5. Assign the person responsible for reporting.

### готовим отчёт, как не потерять требования?

1. Open the application detail page.
2. Check "Отчетность": it lists reporting requirements from the opportunity and marks gaps as `[НУЖНО УТОЧНИТЬ]`.
3. Fill the reporting due date and owner.
4. Save a note with report source links or internal document location.
5. Mark "Отчет подготовлен человеком" only after a person has checked the report.
6. Prepared reports stop appearing as overdue reporting items in the digest.

### заявку уже отправил человек, что отметить?

1. Open the application block.
2. Set the stage to "Человек уже подал заявку".
3. Fill "Кто подал" and "Дата подачи".
4. Add "Срок ответа" if the platform gives one.
5. Save a note with where the confirmation lives.

The system only records the fact. It does not submit the application and does not contact the platform.

### нужен отчёт, как не потерять срок?

1. Open the application block.
2. Set the stage to "Нужен отчет".
3. Fill "Срок отчета".
4. Assign an owner.
5. Save a note with report requirements or a link to the source.
6. Check `digest` or the `/applications` page regularly until the report is done.

## 8. Discovery Workflow

Run Yandex Search discovery:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli discover
```

Run one search query:

```bash
PYTHONPATH=src python3 -m balance_fundraising.cli discover --query "грант для НКО психическое здоровье" --limit 5
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
- `Leads`
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
