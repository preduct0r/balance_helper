# UI Strategy

## Primary User

The primary user is a fundraiser or coordinator who may be far from IT. The interface must feel like an organized workbench, not an admin console.

The user should not need to understand APIs, JSON, model prompts, search endpoints, or storage internals. The UI should translate agent work into familiar actions: check, approve, edit, assign, remind, send for review, and mark done.

## Product Shape

The long-term UI should become a polished operational workspace for fundraising:

- one clear daily dashboard;
- opportunity cards with deadlines and next actions;
- simple review queues for AI findings and drafts;
- document readiness checklist;
- partner/application pipeline;
- human approval controls for every external text or status change.

The UI should prioritize repeated work, low cognitive load, and clear decisions over visual spectacle. "Simple" is not the goal by itself; the goal is comfort, confidence, and fewer missed steps for a non-IT operator.

## Non-IT Design Principles

- Use task language, not system language: "Что нужно сделать" instead of "queue", "pipeline entity", or "JSON payload".
- Show one recommended next action per card.
- Keep statuses few and human-readable.
- Make AI uncertainty visible with labels like `[НУЖНО УТОЧНИТЬ]`, "низкая уверенность", and "нужна проверка".
- Put source links and evidence snippets near extracted facts.
- Never hide human-review boundaries behind automation.
- Avoid dense configuration screens in early versions.
- Prefer safe defaults and editable drafts.
- Use plain Russian labels for production UI unless the team chooses otherwise.

## First UI Slice

The first UI should cover only the current MVP and mirror the operator workflow already exercised by the local smoke script: add a link, analyze it, review extracted facts, open a checklist, open a draft, and check the digest.

- dashboard with urgent deadlines and overdue actions;
- opportunity list with filters by status, deadline, type, and owner;
- opportunity detail page with source, extracted facts, confidence, missing info, checklist, and draft;
- FundWiki editor for approved reusable facts;
- activity history;
- buttons for `approve`, `needs clarification`, `reject`, `assign`, and `mark done`.

CLI and Telegram remain useful for operators, but the non-IT user should be able to complete the main workflow in the web UI.

## Suggested Screens

### Daily Dashboard

- "Сегодня важно": overdue items, deadlines in the next 14 days, drafts waiting for review.
- "Новые находки": opportunities discovered by search and waiting for human review.
- "Документы с пробелами": missing reports, recommendations, legal details, or public links.

### Opportunity List

- Table-like list, not a decorative card grid.
- Columns: name, type, status, deadline, fit, confidence, owner, next action.
- Filters should be visible and simple.

### Opportunity Detail

- Source URL and fetched date.
- Extracted facts grouped by deadline, requirements, documents, reporting, contacts.
- Source snippets shown next to important facts.
- Checklist with checkboxes.
- Draft application text with editable sections.
- Explicit warning when facts are missing or low-confidence.

### FundWiki

- Approved facts about the fund.
- Each fact has a key, text, source, last updated date, and owner.
- Draft generation can only use approved facts.

### Review Queue

- AI findings waiting for approval.
- Drafts waiting for human edit.
- Status changes that need confirmation.

## UI Roadmap

### UI Phase 0: Spreadsheet-First

Use Google Sheets and Telegram while the workflow is still being validated. Keep field names and statuses close to the future UI so migration is straightforward.

### UI Phase 1: Local Web Dashboard

Add a simple local web dashboard that reads from the same store and shows opportunities, deadlines, checklists, and drafts. It may add links and run local heuristic analysis, but it must not send external messages or approve facts.

### UI Phase 2: Review And Edit

Allow the user to review extracted facts, assign owners, update statuses, save notes, and mark checklist items done. Human-review boundaries remain visible: the UI can help prepare drafts and checklists, but it must not send applications or external messages.

### UI Phase 3: Guided Workflows

Add guided flows for "Подать заявку", "Подготовить отчёт", "Связаться с партнёром", and "Проверить новый источник". The first guided workflow is "Подготовить заявку": it combines FundWiki gaps, missing documents, deadline, confidence, owner, status, and safe readiness states without sending anything externally.

Phase 3 has started with the internal application pipeline: the UI now shows `/applications`, lets an operator create a "Заявка" record from an opportunity, tracks stages from "Готовим заявку" to "Ждем ответ", "Нужен отчет", and "Проверить позже", and records dates, owners, notes, and ActivityLog history. The status `submitted_by_human` means a person has already submitted the application outside the service; the system only records that fact.

Phase 3 now continues as a follow-up and reporting workspace: each application has its own detail page for response summary, reporting checklist, reporting state, dates, notes, and history. The first-run screen also shows saved operator observations so confusing UX moments can be reviewed and turned into tasks without leaving the local workspace.

### UI Phase 3A: FundWiki And Readiness

Make "Паспорт фонда" editable in the local web UI and show required reusable facts for applications: mission, audience, programs, start year, impact, legal details, reports, public links, and presentation. Opportunity cards should show "Готовность заявки" so the operator sees exactly what blocks human review.

### UI Phase 4: Multi-Agent Workspace

Add separate workspaces for B2B, private donors, bloggers, events, merch, and paid services while preserving the same dashboard, review queue, and FundWiki patterns.

## Engineering Implications

- Keep service logic outside the UI so CLI, Telegram, and web screens reuse the same services.
- Treat UI labels and statuses as product contracts.
- Design stores and models so each extracted fact can keep evidence and review status.
- Avoid implementing a large UI before the first real user workflow is validated.
- When adding web UI, test it with realistic non-technical tasks, not only component snapshots.
