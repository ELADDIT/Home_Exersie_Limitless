import allure
import pytest


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
