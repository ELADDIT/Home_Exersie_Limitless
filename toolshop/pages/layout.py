"""Shared check that every element a user needs is on the page the journey has just reached."""
import allure
from playwright.sync_api import Page, expect
from pytest_check import check

TEXT_PREFIX = "text="  # an entry like "text=Thanks for your order!" finds an element by its visible text (no data-test exists)
FAST_TIMEOUT_MS = 2_000  # after the first miss the page has clearly loaded, so don't wait the full timeout again


def expect_page_elements(page: Page, page_name: str, elements: list[tuple[str, str]]) -> None:
    """Soft check: every (label, data-test id) in `elements` is visible on the page.

    Missing elements are all reported by label in one failure; the journey carries on
    (pytest-check records the failure and the test fails at the end). A screenshot is attached on a miss.
    """
    missing: list[str] = []
    with check, allure.step(f"{page_name}: all expected elements are shown"):
        for label, ref in elements:
            locator = page.get_by_text(ref[len(TEXT_PREFIX):]) if ref.startswith(TEXT_PREFIX) else page.get_by_test_id(ref)
            try:
                expect(locator.first).to_be_visible(timeout=FAST_TIMEOUT_MS if missing else None)
            except AssertionError:
                missing.append(f"'{label}' ({ref})")
        if missing:
            allure.attach(page.screenshot(), name=f"{page_name}: missing elements", attachment_type=allure.attachment_type.PNG)
            raise AssertionError(f"{page_name}: {len(missing)} expected element(s) not shown: {', '.join(missing)}")
