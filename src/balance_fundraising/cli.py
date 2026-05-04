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
from balance_fundraising.services.b2b import B2BDiscoveryService, analyze_b2b_lead, build_b2b_draft
from balance_fundraising.services.analysis import OpportunityAnalysisService
from balance_fundraising.services.applications import (
    create_application_for_opportunity,
    update_application_dates,
    update_application_note,
    update_application_status,
)
from balance_fundraising.services.checklist import build_checklist
from balance_fundraising.services.demo import seed_demo_store
from balance_fundraising.services.digest import build_digest
from balance_fundraising.services.discovery import DiscoveryService
from balance_fundraising.services.doctor import doctor_has_errors, format_doctor_report, run_doctor
from balance_fundraising.services.draft import build_application_draft
from balance_fundraising.services.leads import create_lead, lead_category_label, lead_status_label, update_lead_status
from balance_fundraising.yandex_api import load_env_file


def main(argv: list[str] | None = None) -> int:
    load_env_file()
    parser = argparse.ArgumentParser(prog="balance-fundraising")
    parser.add_argument("--store-backend", choices=["local", "google"], default=os.getenv("BALANCE_STORE_BACKEND", "local"))
    parser.add_argument("--store", default=os.getenv("BALANCE_STORE_PATH", DEFAULT_STORE_PATH))
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-store")
    subparsers.add_parser("digest")
    discover = subparsers.add_parser("discover")
    discover.add_argument("--query")
    discover.add_argument("--limit", type=int, default=10)
    b2b_radar = subparsers.add_parser("b2b-radar")
    b2b_radar.add_argument("--query")
    b2b_radar.add_argument("--limit", type=int, default=10)
    subparsers.add_parser("doctor")
    subparsers.add_parser("seed-demo")
    subparsers.add_parser("applications")
    subparsers.add_parser("leads")

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

    application_create = subparsers.add_parser("application-create")
    application_create.add_argument("opportunity_id")

    application_status = subparsers.add_parser("application-status")
    application_status.add_argument("application_id")
    application_status.add_argument("status")

    application_show = subparsers.add_parser("application-show")
    application_show.add_argument("application_id")

    application_dates = subparsers.add_parser("application-dates")
    application_dates.add_argument("application_id")
    application_dates.add_argument("--response-due", default="")
    application_dates.add_argument("--reporting-due", default="")
    application_dates.add_argument("--recheck", default="")

    application_note = subparsers.add_parser("application-note")
    application_note.add_argument("application_id")
    application_note.add_argument("text")

    lead_add = subparsers.add_parser("lead-add")
    lead_add.add_argument("--category", default="b2b")
    lead_add.add_argument("--name", required=True)
    lead_add.add_argument("--organization", default="")
    lead_add.add_argument("--url", default="")
    lead_add.add_argument("--description", default="")

    lead_show = subparsers.add_parser("lead-show")
    lead_show.add_argument("lead_id")

    lead_status = subparsers.add_parser("lead-status")
    lead_status.add_argument("lead_id")
    lead_status.add_argument("status")

    b2b_analyze = subparsers.add_parser("b2b-analyze")
    b2b_analyze.add_argument("lead_id")
    b2b_analyze.add_argument("--text-file")

    b2b_draft = subparsers.add_parser("b2b-draft")
    b2b_draft.add_argument("lead_id")

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
        try:
            service = DiscoveryService(store, YandexSearchClient())
            queries = [args.query] if args.query else None
            result = service.discover(queries, limit_per_query=args.limit)
        except RuntimeError as exc:
            print(f"Discovery failed: {exc}")
            return 1
        print(f"Discovery {result.status}: created={result.created_count} existing={result.existing_count}")
        return 0
    if args.command == "b2b-radar":
        try:
            service = B2BDiscoveryService(store, YandexSearchClient())
            queries = [args.query] if args.query else None
            result = service.discover(queries, limit_per_query=args.limit)
        except RuntimeError as exc:
            print(f"B2B discovery failed: {exc}")
            return 1
        print(f"B2B discovery {result.status}: created={result.created_count} existing={result.existing_count}")
        return 0
    if args.command == "seed-demo":
        created = seed_demo_store(store)
        print(f"Seeded demo with {created} opportunities")
        return 0
    if args.command == "applications":
        for application in store.list_applications():
            print(f"{application.id}\t{application.opportunity_id}\t{application.status}\t{application.next_action}")
        return 0
    if args.command == "leads":
        for lead in store.list_leads():
            print(f"{lead.id}\t{lead.category}\t{lead.name}\t{lead.status}\t{lead.next_action}")
        return 0
    if args.command == "application-create":
        application = create_application_for_opportunity(store, args.opportunity_id)
        print(application.id)
        return 0
    if args.command == "application-status":
        application = update_application_status(store, args.application_id, args.status)
        print(f"{application.id}: {application.status}")
        return 0
    if args.command == "application-show":
        application = store.get_application(args.application_id)
        print(f"{application.id}\t{application.opportunity_id}\t{application.status}\t{application.next_action}")
        print(f"owner: {application.owner or 'Не назначен'}")
        print(f"response_due_at: {application.response_due_at or '[НУЖНО УТОЧНИТЬ]'}")
        print(f"reporting_due_at: {application.reporting_due_at or '[НУЖНО УТОЧНИТЬ]'}")
        print(f"recheck_at: {application.recheck_at or '[НУЖНО УТОЧНИТЬ]'}")
        return 0
    if args.command == "application-dates":
        application = update_application_dates(
            store,
            args.application_id,
            response_due_at=args.response_due,
            reporting_due_at=args.reporting_due,
            recheck_at=args.recheck,
        )
        print(f"{application.id}: dates updated")
        return 0
    if args.command == "application-note":
        application = update_application_note(store, args.application_id, args.text)
        print(f"{application.id}: note updated")
        return 0
    if args.command == "lead-add":
        lead = create_lead(
            store,
            category=args.category,
            name=args.name,
            organization=args.organization,
            url=args.url,
            description=args.description,
        )
        print(lead.id)
        return 0
    if args.command == "lead-status":
        lead = update_lead_status(store, args.lead_id, status=args.status)
        print(f"{lead.id}: {lead.status}")
        return 0
    if args.command == "lead-show":
        lead = store.get_lead(args.lead_id)
        print(f"{lead.id}\t{lead_category_label(lead.category)}\t{lead.name}\t{lead_status_label(lead.status)}")
        print(f"organization: {lead.organization}")
        print(f"owner: {lead.owner or 'Не назначен'}")
        print(f"next_action: {lead.next_action}")
        print(f"recheck_at: {lead.recheck_at or '[НУЖНО УТОЧНИТЬ]'}")
        return 0
    if args.command == "b2b-analyze":
        text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else ""
        lead = analyze_b2b_lead(store, args.lead_id, text=text)
        print(f"Analyzed B2B {lead.id}: {lead.fit_for_fund}")
        return 0
    if args.command == "b2b-draft":
        print(build_b2b_draft(store.get_lead(args.lead_id), store.list_fund_wiki()))
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
        print(build_digest(store.list_opportunities(), applications=store.list_applications(), leads=store.list_leads()))
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
