from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class RentalsPage:
    EXPECTED = [("Page title", "page-title")]  # rental cards have no stable data-test; the test checks them itself

    def __init__(self, page: Page):
        self.page = page

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Rentals page", [*HeaderComponent(self.page).expected(), *self.EXPECTED])
