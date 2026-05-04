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
- Upgraded the local web UI plan into a UX-focused operator workspace with review queue, owner/status/note actions, checklist progress, and clearer human-review boundaries.
- Implemented and verified the UX-focused operator workspace with page templates and package-local static CSS; `ux-operator-workspace` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/dev_check.py`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `git diff --check`.
- Added FundWiki passport editing, application readiness blockers, safe readiness states, and `seed-demo` for a local training workflow. `fund-wiki-readiness-workflow` is marked passing after the full test suite and web smoke pass.
- Added the first-run validation screen and internal application pipeline: application creation from opportunities, application list, safe status/date/note updates, ActivityLog entries, application-aware digest, CLI commands, Google/local store methods, and operator docs. `application-pipeline-guided-workflow` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `PYTHONPATH=src python3 scripts/dev_check.py`.
- Added application follow-up and reporting workspace: dedicated application detail pages, response summaries, reporting checklist/state, activity history, feedback statuses, follow-up CLI commands, and application blocker indicators. `application-followup-reporting-workflow` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `PYTHONPATH=src python3 scripts/dev_check.py`.
- Added web opportunity radar: curated manual discovery from `/radar`, CLI `discover --query/--limit`, deduped discovery runs, ActivityLog summaries, sanitized discovery errors, and reviewable `discovered` opportunities. `web-opportunity-radar` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `PYTHONPATH=src python3 scripts/dev_check.py`.
- Added the autonomous global roadmap harness and shared lead workspace: `FundraisingLead`, `Leads` store table, local/Google lead methods, CLI `leads`/`lead-add`/`lead-show`/`lead-status`, web `/leads` list/detail pages, safe lead status/owner/note actions, lead-aware digest and review queue, and roadmap feature entries for future agents. `shared-lead-workspace` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v` and `PYTHONPATH=src python3 scripts/smoke_web_render.py`.
- Added B2B partner agent v1: curated B2B radar, deterministic company fit/risk analysis, first-contact and one-pager drafts from approved FundWiki plus lead evidence, CLI `b2b-radar`/`b2b-analyze`/`b2b-draft`, web `/b2b` workspace and `/b2b/<lead_id>` cards, sanitized B2B discovery errors, and smoke coverage. `b2b-partner-agent` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `PYTHONPATH=src python3 scripts/dev_check.py`.
- Added Paid Services agent v1: `ServiceOffer`, local/Google store methods, offer CLI commands, web `/offers` workspace and detail pages, internal offer gaps/readiness, approved-offer references in B2B drafts, and smoke coverage. `paid-services-agent` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `PYTHONPATH=src python3 scripts/dev_check.py`.
- Added Events And Merch agent v1: curated event radar, `FundraisingLead(category="event")` records, CLI `event-radar`/`events`/`event-add`/`event-show`/`event-checklist`, web `/events` workspace and `/events/<lead_id>` cards, event checklist for deadline, fee, documents, fund description, merch/materials, volunteers, logistics, and post-report, plus sanitized event discovery errors. `events-merch-agent` is marked passing after `PYTHONPATH=src python3 -m unittest discover -s tests -v`, `PYTHONPATH=src python3 scripts/smoke_web_render.py`, and `PYTHONPATH=src python3 scripts/dev_check.py`.
