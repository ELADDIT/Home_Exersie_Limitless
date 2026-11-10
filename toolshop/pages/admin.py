from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class AdminDashboardPage:
    EXPECTED = [("Page title", "page-title"), ("Latest orders heading", "text=Latest orders")]

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Admin dashboard", [*HeaderComponent(self.page).expected(), *self.EXPECTED])
