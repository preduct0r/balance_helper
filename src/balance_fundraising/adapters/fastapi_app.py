from __future__ import annotations

import time
from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from balance_fundraising.adapters.web import WebApp
from balance_fundraising.adapters.web_templates import render_message
from balance_fundraising.services.structured_logging import (
    LoggingConfig,
    configure_logging,
    exception_traceback,
    log_event,
)


def create_fastapi_app(
    store,
    *,
    web_app: Any | None = None,
    log_config: LoggingConfig | None = None,
    search_client_factory: Callable[[], object] | None = None,
    b2b_search_client_factory: Callable[[], object] | None = None,
    event_search_client_factory: Callable[[], object] | None = None,
    blogger_search_client_factory: Callable[[], object] | None = None,
) -> FastAPI:
    configure_logging(log_config)
    adapter = web_app or WebApp(
        store,
        search_client_factory=search_client_factory,
        b2b_search_client_factory=b2b_search_client_factory,
        event_search_client_factory=event_search_client_factory,
        blogger_search_client_factory=blogger_search_client_factory,
    )
    app = FastAPI(title="Balance Fundraising")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - exercised through exception handler
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(
                "web.error",
                str(exc),
                level="ERROR",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                stack_trace=exception_traceback(exc),
            )
            response = HTMLResponse(render_message("Ошибка", "Что-то пошло не так. Подробности записаны в технический лог."), status_code=500)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log_event(
            "web.request",
            "HTTP request handled",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def render_page(request: Request, full_path: str = ""):
        path = _request_path(request, full_path)
        status, html = adapter.render(path)
        return HTMLResponse(html, status_code=status)

    @app.post("/{full_path:path}")
    async def submit_form(request: Request, full_path: str = ""):
        path = _request_path(request, full_path)
        form = await request.form()
        values = {key: str(value) for key, value in form.items()}
        status, result = adapter.post(path, values)
        if status == 303:
            return RedirectResponse(result, status_code=303)
        return HTMLResponse(result, status_code=status)

    return app


def _request_path(request: Request, full_path: str) -> str:
    path = "/" + full_path.strip("/")
    if path == "/":
        return path
    if request.url.query:
        return path + "?" + request.url.query
    return path
