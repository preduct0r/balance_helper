# Quality Rules

- Keep the implementation small and explicit.
- Public commands, env vars, and storage behavior must be documented in `README.md`.
- Detailed operator-facing instructions must be documented and maintained in `docs/USAGE.md`.
- User-facing UI decisions must preserve the non-IT operator assumptions in `docs/UI_STRATEGY.md`.
- Every external integration must have a local/test path.
- Do not weaken acceptance criteria in `docs/feature-list.json`.
- Keep generated content auditable by storing source URLs and source snippets.
- Treat `needs_review` as the default state for newly analyzed opportunities.
- Prefer `null` or `[НУЖНО УТОЧНИТЬ]` over guessed facts.
- Avoid sending PII to LLMs or logs.
