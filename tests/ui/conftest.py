import random

import allure
import pytest

from toolshop.data import PURCHASE_LIMITED


@pytest.fixture(scope="session", autouse=True)
def _use_data_test_attribute(playwright):
    """The shop marks elements with data-test, so page.get_by_test_id() must read that attribute."""
    playwright.selectors.set_test_id_attribute("data-test")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1366, "height": 900}}


@pytest.fixture(autouse=True)
def _final_screenshot(page):
    """Attach the final screen of every UI test (pass or fail) to the report for human review."""
    page.set_default_timeout(15_000)
    yield
    try:
        allure.attach(page.screenshot(full_page=True), name="final screen",
                      attachment_type=allure.attachment_type.PNG)
    except Exception:  # page may already be closed after a crash; never mask the real failure
        pass


# ---- environment guard: the site's bot protection --------------------------------------------
BOT_CHECK_HEADING = "Performing security verification"  # Cloudflare's "verifying you are not a bot" page


@pytest.fixture(scope="session")
def _bot_check_result(browser, base_url) -> str | None:
    """Open the shop once per worker. Returns None if the shop loads, or a reason if Cloudflare's bot check
    is still showing after 15 s (it sometimes clears by itself for a real browser)."""
    page = browser.new_page()
    try:
        page.goto(base_url)
        shop = page.locator("[data-test=product-name]").first
        bot_check = page.get_by_role("heading", name=BOT_CHECK_HEADING)
        shop.or_(bot_check).wait_for(timeout=20_000)
        if not bot_check.is_visible():
            return None
        try:
            shop.wait_for(timeout=15_000)
            return None
        except Exception:
            return (f"KNOWN ISSUE - BLOCKED BY BOT PROTECTION: {base_url} shows Cloudflare's '{BOT_CHECK_HEADING}' page to this "
                    "machine's browser, so the UI test cannot reach the shop. Environment problem, not a product bug "
                    "(seen on GitHub-hosted runners). Run the UI tests from a normal connection (see README).")
    finally:
        page.close()


@pytest.fixture(autouse=True)
def _require_shop_reachable(_bot_check_result):
    """Known issue: on GitHub-hosted runners the site's Cloudflare check blocks the browser. The UI tests are then
    skipped with an explicit reason (reported as a known issue on the dashboard) instead of failing for a reason
    that isn't the store's. They run normally wherever the shop loads."""
    if _bot_check_result:
        pytest.skip(_bot_check_result)


@pytest.fixture
def catalog_products(api):
    """Pick products for a UI journey from the live catalog instead of hard-coding seed names:
    random in-stock, non-rental products from the first catalog page (the page the shop opens on).
    Returns a function: pick(count) -> list of product dicts."""
    def pick(count: int = 1) -> list[dict]:
        r = api.get("/products", params={"page": 1})
        assert r.status_code == 200, f"Setup: product list failed: {r.status_code}"
        pool = [p for p in r.json()["data"]
                if p["in_stock"] and not p["is_rental"] and p["name"] not in PURCHASE_LIMITED
                and " with " not in p["name"].lower()]  # known bug: search can't find names containing "with"
        assert len(pool) >= count, f"Setup: only {len(pool)} in-stock products on the first catalog page"
        picked = random.sample(pool, count)
        allure.dynamic.parameter("products", ", ".join(p["name"] for p in picked))
        return picked
    return pick
