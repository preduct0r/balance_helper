from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HarnessDocsTests(unittest.TestCase):
    def test_readme_mentions_public_commands_and_env(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for command in ["init-store", "discover", "add-link", "analyze", "checklist", "draft", "digest", "bot", "doctor"]:
            self.assertIn(command, readme)
        for env in ["YANDEX_API_KEY", "YANDEX_FOLDER_ID", "YANDEX_LLM_MODEL_URI", "TELEGRAM_BOT_TOKEN", "BALANCE_STORE_BACKEND"]:
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
            "UI Phase 1",
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
        ]:
            self.assertIn(phrase, usage)


if __name__ == "__main__":
    unittest.main()
