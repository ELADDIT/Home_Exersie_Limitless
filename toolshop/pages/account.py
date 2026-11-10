from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class AccountPage:
    EXPECTED = [("Page title", "page-title"), ("Favorites tab", "nav-favorites"), ("Profile tab", "nav-profile"),
                ("Invoices tab", "nav-invoices"), ("Messages tab", "nav-messages")]

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")

    def expect_loaded(self, cart_filled: bool = False) -> None:
        expect_page_elements(self.page, "Account page", [*HeaderComponent(self.page).expected(cart_filled), *self.EXPECTED])
