from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HarnessDocsTests(unittest.TestCase):
    def test_readme_mentions_public_commands_and_env(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for command in [
            "init-store",
            "discover",
            "--query",
            "--limit",
            "add-link",
            "analyze",
            "checklist",
            "draft",
            "digest",
            "bot",
            "doctor",
            "web",
            "seed-demo",
            "applications",
            "application-create",
            "application-status",
            "application-show",
            "application-dates",
            "application-note",
            "leads",
            "lead-add",
            "lead-show",
            "lead-status",
            "b2b-radar",
            "b2b-analyze",
            "b2b-draft",
            "offers",
            "offer-add",
            "offer-show",
            "offer-status",
            "offer-note",
            "event-radar",
            "events",
            "event-add",
            "event-show",
            "event-checklist",
            "blogger-radar",
            "bloggers",
            "blogger-add",
            "blogger-show",
            "blogger-analyze",
            "blogger-checklist",
            "blogger-draft",
            "donor-campaigns",
            "donor-campaign-add",
            "donor-campaign-show",
            "donor-campaign-status",
            "donor-campaign-note",
            "donor-campaign-draft",
        ]:
            self.assertIn(command, readme)
        for phrase in [
            "cross-agent dashboard",
            "unified review queue",
            "all implemented modules",
        ]:
            self.assertIn(phrase, readme)
        for env in [
            "YANDEX_API_KEY",
            "YANDEX_FOLDER_ID",
            "YANDEX_LLM_MODEL_URI",
            "TELEGRAM_BOT_TOKEN",
            "BALANCE_STORE_BACKEND",
            "BALANCE_WEB_HOST",
            "BALANCE_WEB_PORT",
        ]:
            self.assertIn(env, readme)

    def test_agents_links_key_docs(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for path in [
            "ARCHITECTURE.md",
            "docs/TESTING.md",
            "docs/QUALITY.md",
            "docs/ROADMAP.md",
            "docs/UI_STRATEGY.md",
            "docs/USAGE.md",
            "docs/exec-plans/active/mvp-platform-applications-agent.md",
            "docs/agent-progress.md",
            "docs/feature-list.json",
        ]:
            self.assertIn(path, agents)

    def test_feature_list_valid_json(self) -> None:
        data = json.loads((ROOT / "docs/feature-list.json").read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        self.assertTrue(data)
        for item in data:
            self.assertIn("acceptance_steps", item)
            self.assertIn("passes", item)

    def test_roadmap_captures_future_agent_system(self) -> None:
        roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
        for phrase in [
            "Product North Star",
            "MVP: Platforms And Applications",
            "Autonomous Development",
            "Shared Lead Workspace",
            "B2B Agent",
            "Private Donor Agent",
            "Blogger And Ambassador Agent",
            "Events And Merch Agent",
            "Paid Services Agent",
        ]:
            self.assertIn(phrase, roadmap)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        domain = (ROOT / "docs/FUNDRAISING_DOMAIN.md").read_text(encoding="utf-8")
        self.assertIn("docs/ROADMAP.md", readme)
        self.assertIn("docs/ROADMAP.md", domain)

    def test_ui_strategy_is_linked_and_operator_centered(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
        quality = (ROOT / "docs/QUALITY.md").read_text(encoding="utf-8")
        ui_strategy = (ROOT / "docs/UI_STRATEGY.md").read_text(encoding="utf-8")
        for document in [agents, readme, roadmap, quality]:
            self.assertIn("docs/UI_STRATEGY.md", document)
        for phrase in [
            "Primary User",
            "non-IT",
            "operator workflow",
            "Daily Dashboard",
            "Opportunity Detail",
            "Review Queue",
            "Local Web Dashboard",
            "Review And Edit",
            "Human-review boundaries",
            "Multi-Agent Workspace",
        ]:
            self.assertIn(phrase, ui_strategy)

    def test_usage_guide_is_linked_and_detailed(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        usage = (ROOT / "docs/USAGE.md").read_text(encoding="utf-8")
        self.assertIn("docs/USAGE.md", readme)
        self.assertIn("Keep `docs/USAGE.md` current", agents)
        for phrase in [
            "Local Setup",
            "Environment Variables",
            "Local JSON Store",
            "Basic Workflow",
            "Discovery Workflow",
            "Telegram Bot",
            "Google Sheets Store",
            "Human Review Boundary",
            "Я нашла ссылку",
            "BALANCE_STORE_BACKEND",
            "Local Web UI",
            "Web scenario for a non-IT operator",
            "Паспорт фонда",
            "тренировочный",
            "мы реально подаём заявку",
            "заявку уже отправил человек",
            "нужен отчёт",
            "ждём ответ",
            "получили отказ",
            "заявку приняли",
            "готовим отчёт",
            "Радар",
            "discover --query",
            "discover --limit",
            "Контакты и направления",
            "lead-add",
            "lead-status",
            "B2B",
            "b2b-radar",
            "b2b-analyze",
            "b2b-draft",
            "Услуги",
            "offer-add",
            "offer-status",
            "offer-note",
            "Мероприятия",
            "event-radar",
            "event-add",
            "event-checklist",
            "без складского учета",
            "Блогеры",
            "blogger-radar",
            "blogger-add",
            "blogger-checklist",
            "blogger-draft",
            "этический чек-лист",
            "без рассылок",
            "Доноры",
            "donor-campaign-add",
            "donor-campaign-draft",
            "без персональных данных",
            "без отправки сообщений",
            "единый рабочий стол",
            "cross-agent digest",
            "общая очередь проверки",
            "BALANCE_WEB_HOST",
            "BALANCE_WEB_PORT",
        ]:
            self.assertIn(phrase, usage)

    def test_global_roadmap_exec_plan_exists(self) -> None:
        active = (ROOT / "docs/exec-plans/active/global-roadmap-autonomous-development.md").read_text(encoding="utf-8")
        feature_list = json.loads((ROOT / "docs/feature-list.json").read_text(encoding="utf-8"))
        feature_ids = {item["id"]: item for item in feature_list}
        for feature_id in [
            "shared-lead-workspace",
            "b2b-partner-agent",
            "paid-services-agent",
            "events-merch-agent",
            "blogger-ambassador-agent",
            "private-donor-campaign-agent",
            "cross-agent-operator-dashboard",
            "final-validation-and-hardening",
        ]:
            self.assertIn(feature_id, feature_ids)
            self.assertIn(feature_id, active)
        self.assertIn("first roadmap feature with `passes: false`", active)


if __name__ == "__main__":
    unittest.main()
