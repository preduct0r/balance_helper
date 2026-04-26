from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balance_fundraising.adapters.local_json_store import LocalJsonStore
from balance_fundraising.adapters.telegram_bot import TelegramCommandHandler
from balance_fundraising.domain import Opportunity
from balance_fundraising.services.analysis import OpportunityAnalysisService
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.draft import build_application_draft


class LocalIntegrationTests(unittest.TestCase):
    def test_local_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            opportunity = Opportunity.from_url("https://example.org/vk")
            store.upsert_opportunity(opportunity)
            analyzed = OpportunityAnalysisService(store).analyze_opportunity(
                opportunity.id,
                text="VK Добро регистрация фондов. Благотворительные фонды НКО. Нужны устав, отчетность и рекомендации.",
            )
            self.assertEqual(analyzed.status, "needs_review")
            self.assertIn("Отчетность фонда", build_checklist(analyzed))
            self.assertIn("Черновик заявки", build_application_draft(analyzed, store.list_fund_wiki()))
            self.assertIn("дедлайн не указан", build_digest(store.list_opportunities()))

    def test_telegram_handlers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJsonStore(Path(tmp) / "store.json")
            store.init_store()
            handler = TelegramCommandHandler(store)
            response = handler.handle("/add_link https://example.org")
            opportunity_id = response.split()[-1]
            self.assertIn("Добавлено", response)
            self.assertIn("Статус обновлен", handler.handle(f"/status {opportunity_id} accepted"))
            self.assertIn("Черновик заявки", handler.handle(f"/draft {opportunity_id}"))


if __name__ == "__main__":
    unittest.main()

