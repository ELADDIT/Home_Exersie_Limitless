from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class InvoicesPage:
    """My account -> Invoices: one table row per invoice (no data-test on rows or cells)."""

    EXPECTED = [("Page title", "page-title"), ("Invoice Number column", "text=Invoice Number"),
                ("Total column", "text=Total"), ("Invoice Date column", "text=Invoice Date")]

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")
        self.rows = page.locator("table tbody tr")

    def open_from_menu(self) -> None:
        """Header user menu -> 'My invoices', like a customer would."""
        HeaderComponent(self.page).open_user_menu()
        self.page.get_by_test_id("nav-my-invoices").click()

    def row_with(self, text: str):
        return self.rows.filter(has_text=text)

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Invoices page", [*HeaderComponent(self.page).expected(), *self.EXPECTED])
