# Exec Plan: Global Roadmap Autonomous Development

## Goal

Continue the fundraising roadmap without waiting for real operator validation until the final validation phase. Development is local-first: tests, demo data, and mocked integrations are the main proof while external sends remain forbidden.

## Autonomous Rule

When starting a new roadmap session, read `AGENTS.md`, this plan, `docs/agent-progress.md`, and `docs/feature-list.json`. Pick the first roadmap feature with `passes: false`, add tests first, implement only that feature, run `scripts/dev_check.py`, then update docs, progress, and the feature list.

## Roadmap Features

- [x] `shared-lead-workspace`: common lead model, store methods, CLI, web list/detail, digest, and review queue.
- [x] `b2b-partner-agent`: company leads, fit analysis, risk checks, and human-reviewed first-contact drafts.
- [x] `paid-services-agent`: reviewed offers for lectures, workshops, internships, and educational products.
- [x] `events-merch-agent`: event/market lead workflow with practical checklist and post-report notes.
- [x] `blogger-ambassador-agent`: creator leads with ethics/risk checklist and safe collaboration drafts.
- [x] `private-donor-campaign-agent`: segment-level donor campaigns without personal donor data.
- [x] `cross-agent-operator-dashboard`: unified dashboard, review queue, and digest across implemented modules.
- [x] `fastapi-structured-logging-hardening`: FastAPI web runtime and sanitized JSONL technical logs.
- [x] `docker-persistent-runtime`: Docker Compose runtime with persistent host-mounted data and logs.
- [ ] `final-validation-and-hardening`: real-world validation, integration hardening, and UI/deployment decisions.

## Defaults

- Local JSON remains the default development store.
- Google Sheets adapters must be mock-tested only.
- No emails, partner messages, forms, Telegram outbound messages, or report submissions are added.
- Drafts use approved FundWiki, source evidence, and explicit missing markers.
- Beneficiary PII must not enter prompts, logs, demo seeds, or fixtures.

## Done Means

- The implemented roadmap feature has tests for domain/store/service, CLI, web, docs, and smoke where applicable.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` passes.
- `PYTHONPATH=src python3 scripts/smoke_web_render.py` passes.
- `PYTHONPATH=src python3 scripts/dev_check.py` passes.
- `docs/feature-list.json` marks only verified work as `passes: true`.
