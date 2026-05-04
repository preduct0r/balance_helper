from __future__ import annotations

import argparse
import os
from pathlib import Path

from balance_fundraising.adapters.store_factory import build_store_config, create_store
from balance_fundraising.adapters.telegram_bot import TelegramCommandHandler, run_polling_bot
from balance_fundraising.adapters.web import run_web_server
from balance_fundraising.app_defaults import DEFAULT_STORE_PATH
from balance_fundraising.clients.yandex_llm import YandexLLMClient
from balance_fundraising.clients.yandex_search import YandexSearchClient
from balance_fundraising.domain import ActivityLogEntry, Opportunity
from balance_fundraising.services.analysis import OpportunityAnalysisService
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.demo import seed_demo_store
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.discovery import DiscoveryService
from balance_fundraising.services.doctor import doctor_has_errors, format_doctor_report, run_doctor
from balance_fundraising.services.draft import build_application_draft
from balance_fundraising.yandex_api import load_env_file


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = argparse.ArgumentParser(prog="balance-fundraising")
    parser.add_argument("--store-backend", choices=["local", "google"], default=os.getenv("BALANCE_STORE_BACKEND", "local"))
    parser.add_argument("--store", default=os.getenv("BALANCE_STORE_PATH", DEFAULT_STORE_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-store")
    subparsers.add_parser("digest")
    subparsers.add_parser("discover")
    subparsers.add_parser("doctor")
    subparsers.add_parser("seed-demo")

    add_link = subparsers.add_parser("add-link")
    add_link.add_argument("url")

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("opportunity_id")
    analyze.add_argument("--text-file")
    analyze.add_argument("--use-llm", action="store_true")

    checklist = subparsers.add_parser("checklist")
    checklist.add_argument("opportunity_id")

    draft = subparsers.add_parser("draft")
    draft.add_argument("opportunity_id")

    subparsers.add_parser("bot")

    web = subparsers.add_parser("web")
    web.add_argument("--host", default=os.getenv("BALANCE_WEB_HOST", "127.0.0.1"))
    web.add_argument("--port", type=int, default=int(os.getenv("BALANCE_WEB_PORT", "8080")))

    args = parser.parse_args(argv)
    store_config = build_store_config(backend=args.store_backend, local_path=args.store)

    if args.command == "doctor":
        checks = run_doctor(store_config)
        print(format_doctor_report(checks))
        return 1 if doctor_has_errors(checks) else 0

    store = create_store(store_config)
    store.init_store()

    if args.command == "init-store":
        print(f"Initialized {store_config.backend} store")
        return 0
    if args.command == "add-link":
        opportunity = Opportunity.from_url(args.url)
        store.upsert_opportunity(opportunity)
        store.add_activity(ActivityLogEntry.today(action="add_link", entity_id=opportunity.id, details=args.url))
        print(opportunity.id)
        return 0
    if args.command == "discover":
        service = DiscoveryService(store, YandexSearchClient())
        discovered = service.discover()
        print(f"Discovered {len(discovered)} opportunities")
        return 0
    if args.command == "seed-demo":
        created = seed_demo_store(store)
        print(f"Seeded demo with {created} opportunities")
        return 0
    if args.command == "analyze":
        text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else None
        llm = YandexLLMClient() if args.use_llm else None
        opportunity = OpportunityAnalysisService(store, llm_client=llm).analyze_opportunity(
            args.opportunity_id,
            text=text,
            use_llm=args.use_llm,
        )
        print(f"Analyzed {opportunity.id}: {opportunity.name}")
        return 0
    if args.command == "checklist":
        print(build_checklist(store.get_opportunity(args.opportunity_id)))
        return 0
    if args.command == "draft":
        print(build_application_draft(store.get_opportunity(args.opportunity_id), store.list_fund_wiki()))
        return 0
    if args.command == "digest":
        print(build_digest(store.list_opportunities()))
        return 0
    if args.command == "bot":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("Set TELEGRAM_BOT_TOKEN to run the bot.")
        run_polling_bot(token, TelegramCommandHandler(store))
        return 0
    if args.command == "web":
        run_web_server(store, host=args.host, port=args.port)
        return 0
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
