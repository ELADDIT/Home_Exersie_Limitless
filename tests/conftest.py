"""Shared fixtures for API and UI tests.

Data isolation rule: anything that changes state (cart, order, account) runs as a
fresh customer created by the `customer` fixture. The public demo customer accounts
are shared with other people on the internet and are never used. The demo admin
account is used read-only.
"""
import inspect
import random

import allure
import pytest

from toolshop.api import ToolshopApi
from toolshop.config import Settings
from toolshop.data import Customer

UI_TEST_BUDGET = 10  # brief: 5-10 browser tests in total, each parametrized case counts


def pytest_addoption(parser):
    parser.addoption("--env", default=None, help="Target environment (prod, with-bugs). Overrides TOOLSHOP_ENV.")


# ---- report metadata: set here once, so every test (including new ones) gets it for free ----
# Product area per test module; the report's "Behaviors" view groups tests by it.
FEATURE_BY_MODULE = {
    "test_products": "Catalog", "test_catalog": "Catalog",
    "test_cart": "Cart", "test_orders": "Orders & invoices", "test_payment": "Payment",
    "test_auth": "Login", "test_tokens": "Login tokens",
    "test_access_control": "Access control", "test_access_writes": "Access control",
    "test_registration": "Registration", "test_boundaries": "Input validation (boundaries)",
    "test_minor_features": "Minor features (UI/UX)",
    "test_account_security": "Account security", "test_checkout_rules": "Orders & invoices",
}
# The UI journeys file covers several areas, so map by a keyword in the test name (first match wins).
FEATURE_BY_UI_KEYWORD = [("access", "Access control"), ("checkout", "Checkout"), ("login", "Login"),
                         ("registration", "Registration"), ("catalog", "Catalog"), ("cart", "Cart")]
CRITICAL_FEATURES = {"Account security", "Access control", "Login tokens", "Checkout", "Orders & invoices", "Payment"}


def feature_of(item) -> str:
    module = item.module.__name__.rsplit(".", 1)[-1]
    if module in FEATURE_BY_MODULE:
        return FEATURE_BY_MODULE[module]
    name = item.originalname.lower()
    return next((f for key, f in FEATURE_BY_UI_KEYWORD if key in name), "Other")


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
        test_set, feature = sets.pop(), feature_of(item)
        severity = ("blocker" if test_set == "sanity" else "critical" if feature in CRITICAL_FEATURES else "normal")
        item.add_marker(allure.epic("Toolshop"))
        item.add_marker(allure.feature(feature))
        item.add_marker(allure.story(test_set))
        item.add_marker(allure.severity(severity))
        item.add_marker(allure.label("layer", "ui" if "/tests/ui/" in path else "api"))
        if item.get_closest_marker("xfail"):
            item.add_marker(allure.tag("known-bug"))
        if not item.function.__doc__ and item.module.__doc__:  # report description: test docstring, else module's
            item.add_marker(pytest.mark.allure_description(inspect.cleandoc(item.module.__doc__)))
    if ui_count > UI_TEST_BUDGET:
        raise pytest.UsageError(f"{ui_count} UI test cases collected; the budget is {UI_TEST_BUDGET}")


@pytest.hookimpl(hookwrapper=True, trylast=True)  # innermost wrapper: runs after Allure sets its defaults
def pytest_runtest_call(item):
    """Readable report title for every test, e.g. 'Customer cannot read another customers favorite [guest]'."""
    title = item.originalname.removeprefix("test_").replace("_", " ").capitalize()
    case = getattr(getattr(item, "callspec", None), "id", "")
    allure.dynamic.title(f"{title} [{case}]" if case else title)
    yield


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
    """For tests that PLACE ORDERS. Orders should reduce stock (the app currently doesn't: known bug), so we spread purchases:
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
