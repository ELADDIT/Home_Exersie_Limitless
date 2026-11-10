from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class ComparisonPage:
    EXPECTED = [("Page title", "comparison-title"), ("Comparison table", "comparison-table"),
                ("Product name", "product-name"), ("Price row", "compare-price"),
                ("Clear all button", "clear-comparison")]

    def __init__(self, page: Page):
        self.page = page
        self.table = page.get_by_test_id("comparison-table")
        self.product_names = page.get_by_test_id("product-name")

    def expect_loaded(self, cart_filled: bool = False) -> None:
        expect_page_elements(self.page, "Comparison page", [*HeaderComponent(self.page).expected(cart_filled), *self.EXPECTED])
