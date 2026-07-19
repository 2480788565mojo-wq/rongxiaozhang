import asyncio

from fastapi import FastAPI

from app.api.v1.router import api_health, api_router


def test_health_endpoint():
    assert asyncio.run(api_health()) == {"status": "ok", "version": "2.0.0"}


def test_all_planned_api_routes_are_registered():
    application = FastAPI()
    application.include_router(api_router)
    schema = application.openapi()
    http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
    routes = {
        (method.upper(), path)
        for path, operations in schema["paths"].items()
        for method in operations
        if method in http_methods
    }
    expected = {
        ("POST", "/auth/login"),
        ("GET", "/auth/me"),
        ("GET", "/accounts"),
        ("POST", "/accounts"),
        ("PUT", "/accounts/{account_id}"),
        ("DELETE", "/accounts/{account_id}"),
        ("POST", "/bills/transcribe"),
        ("POST", "/bills/confirm"),
        ("GET", "/bills"),
        ("GET", "/bills/{bill_id}"),
        ("PUT", "/bills/{bill_id}"),
        ("DELETE", "/bills/{bill_id}"),
        ("GET", "/ledgers"),
        ("POST", "/ledgers"),
        ("GET", "/ledgers/{ledger_id}"),
        ("POST", "/ledgers/{ledger_id}/join"),
        ("POST", "/ledgers/{ledger_id}/settle"),
        ("POST", "/ledgers/{ledger_id}/invite/rotate"),
        ("GET", "/budgets"),
        ("PUT", "/budgets"),
        ("GET", "/budgets/status"),
        ("GET", "/categories"),
        ("POST", "/categories"),
        ("PUT", "/categories/{category_id}"),
        ("DELETE", "/categories/{category_id}"),
        ("GET", "/stats/overview"),
        ("GET", "/stats/trend"),
        ("GET", "/stats/category"),
        ("POST", "/insights/generate"),
        ("GET", "/insights"),
        ("GET", "/insights/{insight_id}"),
        ("GET", "/sse/subscribe"),
        ("GET", "/health"),
    }

    assert expected <= routes
    assert len(routes) == 33
