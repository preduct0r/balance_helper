# Exec Plan: MVP Platform Applications Agent

## Goal

Implement a tested Python MVP that helps a fundraiser discover, analyze, track, and draft applications for NKO platforms.

## Checklist

- [x] Create harness docs and agent instructions.
- [x] Add domain models and local storage.
- [x] Add Yandex LLM helpers compatible with the existing example script.
- [x] Add Yandex Search client and parser.
- [x] Add text extraction and structured JSON parsing.
- [x] Add services for discovery, analysis, checklists, drafts, and digest.
- [x] Add CLI and Telegram command handlers.
- [x] Add tests and fixtures.
- [x] Add dev check script.

## Follow-Up: Operator Workflow

- [x] Add selectable store backend for local and Google modes.
- [x] Add `doctor` diagnostics without external network calls.
- [x] Add offline operator smoke workflow.
- [x] Add operator recipes for non-IT usage.
- [x] Tie the first future UI slice to the same operator workflow.
- [x] Add first local web UI for the operator workflow.
- [x] Add UX-focused review/edit workspace on top of the local web UI.

## Done Means

- Local tests pass without external services.
- README documents every public command and env var.
- Feature list is valid JSON.
- `scripts/yandex_llm_example.py` can import its helper modules.
- `scripts/smoke_operator_workflow.py` completes without external services.
- `scripts/smoke_web_render.py` completes without external services.
