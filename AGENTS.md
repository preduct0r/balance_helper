# Agent Guide

This repository is built to be safe for long-running coding agents. Read this file first, then read the roadmap, `docs/agent-progress.md`, `docs/feature-list.json`, and the active exec plan before making changes.

## Required Context

- Architecture: `ARCHITECTURE.md`
- Testing: `docs/TESTING.md`
- Quality rules: `docs/QUALITY.md`
- Domain map: `docs/FUNDRAISING_DOMAIN.md`
- System roadmap: `docs/ROADMAP.md`
- Detailed service usage: `docs/USAGE.md`
- Active plan: `docs/exec-plans/active/mvp-platform-applications-agent.md`
- Progress log: `docs/agent-progress.md`
- Feature list: `docs/feature-list.json`

## Behavioral Guidelines

### Think Before Coding

- Do not assume. Do not hide confusion. Surface tradeoffs.
- State assumptions explicitly before implementation.
- If multiple interpretations exist, present them instead of picking silently.
- If a simpler approach exists, say so.
- If something is unclear and cannot be discovered from the repo, stop and ask.

### Simplicity First

- Write the minimum code that solves the verified goal.
- Do not add speculative features, abstractions, or configurability.
- Avoid error handling for impossible scenarios.
- If a change is much larger than the task requires, simplify it.

### Surgical Changes

- Touch only what the task requires.
- Do not refactor adjacent code unless it is necessary.
- Match existing style.
- Remove only unused code introduced by your own change.
- Mention unrelated dead code; do not delete it unless asked.

### Goal-Driven Execution

- Turn every task into verifiable goals.
- Add or update tests with the feature.
- Keep `README.md` current when commands, env vars, storage shape, or behavior change.
- Keep `docs/USAGE.md` current with detailed operator-facing instructions whenever setup, CLI, Telegram, storage, Yandex, Google Sheets, or workflow behavior changes.
- Keep `docs/agent-progress.md` current when a meaningful decision, blocker, or completion state changes.
- Do not mark `passes: true` in `docs/feature-list.json` until the related tests/checks pass.

## Safety Rules

- Never send personal data about beneficiaries to an LLM.
- Generated applications, checklists, status changes, and outgoing communications require human review.
- External clients must be mockable; tests must not call real Yandex, Google, or Telegram services.
- Prefer the local JSON store for tests and development.
- Keep changes small enough that every changed line traces to the user's request.
