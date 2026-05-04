from __future__ import annotations

from balance_fundraising.domain import ActivityLogEntry, Opportunity
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.draft import build_application_draft


class TelegramCommandHandler:
    def __init__(self, store) -> None:
        self.store = store

    def handle(self, message: str) -> str:
        parts = message.strip().split()
        if not parts:
            return "Команда не распознана."
        command = parts[0]
        if command == "/digest":
            return build_digest(self.store.list_opportunities(), leads=self.store.list_leads())
        if command == "/add_link" and len(parts) >= 2:
            opportunity = Opportunity.from_url(parts[1])
            self.store.upsert_opportunity(opportunity)
            self.store.add_activity(ActivityLogEntry.today(action="add_link", entity_id=opportunity.id, details=opportunity.url))
            return f"Добавлено: {opportunity.id}"
        if command == "/checklist" and len(parts) >= 2:
            return build_checklist(self.store.get_opportunity(parts[1]))
        if command == "/draft" and len(parts) >= 2:
            return build_application_draft(self.store.get_opportunity(parts[1]), self.store.list_fund_wiki())
        if command == "/status" and len(parts) >= 3:
            opportunity = self.store.update_opportunity_fields(parts[1], {"status": parts[2]})
            self.store.add_activity(ActivityLogEntry.today(action="status", entity_id=opportunity.id, details=parts[2]))
            return f"Статус обновлен: {opportunity.id} -> {opportunity.status}"
        return "Команда не распознана или не хватает аргументов."


def run_polling_bot(token: str, handler: TelegramCommandHandler) -> None:
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError as exc:
        raise RuntimeError("Install telegram extra to run the bot: pip install .[telegram]") from exc

    async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message and update.message.text:
            await update.message.reply_text(handler.handle(update.message.text))

    app = Application.builder().token(token).build()
    for command in ["digest", "add_link", "checklist", "draft", "status"]:
        app.add_handler(CommandHandler(command, reply))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    app.run_polling()
