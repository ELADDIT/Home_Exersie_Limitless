"""Shared fixtures for API and UI tests.

Data isolation rule: anything that changes state (cart, order, account) runs as a
fresh customer created by the `customer` fixture. The public demo customer accounts
are shared with other people on the internet and are never used. The demo admin
account is used read-only.
"""
import random

import allure
import pytest

from toolshop.api import ToolshopApi
from toolshop.config import Settings
from toolshop.data import Customer

UI_TEST_BUDGET = 10  # brief: 5-10 browser tests in total, each parametrized case counts


def pytest_addoption(parser):
    parser.addoption("--env", default=None, help="Target environment (prod, with-bugs). Overrides TOOLSHOP_ENV.")


@pytest.hookimpl(tryfirst=True)  # run before -m deselection so the budget counts the whole suite
def pytest_collection_modifyitems(config, items):
    ui_count = 0
    for item in items:
        path = str(item.path)
        if "/tests/ui/" in path:
            item.add_marker(pytest.mark.ui)
            ui_count += 1
        elif "/tests/api/" in path:
            item.add_marker(pytest.mark.api)
        sets = {m.name for m in item.iter_markers()} & {"sanity", "progression"}
        if len(sets) != 1:
            raise pytest.UsageError(f"{item.nodeid}: mark the test with exactly one of @pytest.mark.sanity / progression")
    if ui_count > UI_TEST_BUDGET:
        raise pytest.UsageError(f"{ui_count} UI test cases collected; the budget is {UI_TEST_BUDGET}")


@pytest.fixture(scope="session")
def settings(pytestconfig) -> Settings:
    env = pytestconfig.getoption("--env")
    return Settings(env=env) if env else Settings()


@pytest.fixture(scope="session")
def base_url(settings) -> str:
    """Overrides pytest-base-url so Playwright's page.goto('/path') targets the chosen env."""
    return settings.base_url


@pytest.fixture(scope="session")
def api(settings) -> ToolshopApi:
    """Guest (unauthenticated) API client."""
    return ToolshopApi(settings.api_url, settings.request_timeout)


@pytest.fixture
def customer(api) -> Customer:
    """A brand-new registered customer, logged in via the API (token on .token)."""
    c = api.register(Customer())
    c.token = api.login(c.email, c.password)
    return c


@pytest.fixture
def customer_api(api, customer) -> ToolshopApi:
    return api.as_token(customer.token)


@pytest.fixture(scope="session")
def admin_credentials(settings) -> tuple[str, str]:
    if not (settings.admin_email and settings.admin_password):
        pytest.fail("Admin credentials missing: set TOOLSHOP_ADMIN_EMAIL and TOOLSHOP_ADMIN_PASSWORD "
                    "(see README). Failing rather than skipping so a green run is never partial.")
    return settings.admin_email, settings.admin_password.get_secret_value()


@pytest.fixture(scope="session")
def admin_api(api, admin_credentials) -> ToolshopApi:
    return api.as_token(api.login(*admin_credentials))


@pytest.fixture(scope="session")
def products(api) -> list[dict]:
    """Two purchasable products looked up from the live catalog (for cart tests; carts don't use stock)."""
    return api.in_stock_products(2)


MAX_ORDER_QUANTITY = 3  # small, but > 1 so multi-unit orders are exercised
PURCHASE_LIMITED = {"Thor Hammer"}  # app rule: max one per customer, so the generic picker skips it


@pytest.fixture
def pick_purchases(api, admin_api):
    """For tests that PLACE ORDERS. Orders reduce stock on the shared site, so we spread purchases:
    random products from the first catalog page, each with a random quantity 1..3 that never exceeds
    the real stock (read via the admin API). Returns a function: pick(count) -> [(product, quantity)]."""
    def pick(count: int = 1) -> list[tuple[dict, int]]:
        r = api.get("/products", params={"page": 1})
        assert r.status_code == 200, f"Setup: product list failed: {r.status_code}"
        candidates = [p for p in r.json()["data"]
                      if p["in_stock"] and not p["is_rental"] and p["name"] not in PURCHASE_LIMITED]
        random.shuffle(candidates)
        picks = []
        for product in candidates:
            stock = admin_api.stock_level(product["id"])
            if stock >= 1:
                picks.append((product, random.randint(1, min(MAX_ORDER_QUANTITY, stock))))
            if len(picks) == count:
                with allure.step("Picked: " + ", ".join(f"{q} x {p['name']}" for p, q in picks)):
                    return picks
        pytest.fail(f"Setup: fewer than {count} products in stock on catalog page 1 (shared site out of stock?)")
    return pick
