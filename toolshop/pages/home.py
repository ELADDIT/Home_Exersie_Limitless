import re

from playwright.sync_api import Page, expect

from .header import HeaderComponent
from .layout import expect_page_elements


class HomePage:
    """Catalog: search, category filter, sorting and product cards."""

    EXPECTED = [("Sort select", "sort"), ("Search field", "search-query"),
                ("Search button", "search-submit"), ("Product card name", "product-name"),
                ("Product card price", "product-price"), ("Compare button on a card", "compare-btn")]

    def __init__(self, page: Page):
        self.page = page
        self.search_input = page.get_by_test_id("search-query")
        self.search_button = page.get_by_test_id("search-submit")
        self.sort_select = page.get_by_test_id("sort")
        self.product_names = page.get_by_test_id("product-name")
        self.product_prices = page.get_by_test_id("product-price")
        self.max_price_slider = page.get_by_role("slider").nth(1)
        self.compare_buttons = page.get_by_test_id("compare-btn")
        self.comparison_bar = page.get_by_test_id("comparison-bar")
        self.compare_now_link = page.get_by_test_id("compare-link")

    @staticmethod
    def _is_product_query(response) -> bool:
        """The catalog is reloaded by one request to the product list (a QUERY call)."""
        return response.url.endswith("/products")

    def open(self) -> None:
        """Open the shop and wait until the catalog is on screen, like a user would before interacting.
        Without this, a search fired during the initial load gets overwritten when that load finishes."""
        self.page.goto("/")
        expect(self.product_names.first).to_be_visible()

    def expect_loaded(self, cart_filled: bool = False) -> None:
        expect_page_elements(self.page, "Home page", [*HeaderComponent(self.page).expected(cart_filled), *self.EXPECTED])

    def search(self, text: str) -> None:
        with self.page.expect_response(lambda r: "/products/search" in r.url):
            self.search_input.fill(text)
            self.search_button.click()

    def product_card_name(self, name: str):
        """The card whose name is exactly `name` ("Hammer" must not match "Claw Hammer")."""
        return self.product_names.filter(has_text=re.compile(rf"^\s*{re.escape(name)}\s*$"))

    def open_product(self, name: str) -> None:
        self.product_card_name(name).first.click()

    def filter_by_category(self, category: str) -> None:
        # the filter panel has no data-test per category label, so use the visible label text
        with self.page.expect_response(self._is_product_query):
            self.page.get_by_label(category, exact=True).check()

    def sort_by(self, label: str) -> None:
        with self.page.expect_response(self._is_product_query):
            self.sort_select.select_option(label=label)

    def displayed_prices(self) -> list[float]:
        return [float(t.lstrip("$")) for t in self.product_prices.all_inner_texts()]

    def lower_max_price(self, steps: int) -> int:
        """Move the price slider's upper handle down with the keyboard (one PageDown per step).
        Every step reloads the list, so wait for each reload; otherwise an older response can win."""
        self.max_price_slider.focus()
        for _ in range(steps):
            with self.page.expect_response(self._is_product_query):
                self.max_price_slider.press("PageDown")
        return int(self.max_price_slider.get_attribute("aria-valuenow"))

    def filter_by_brand(self, brand: str) -> None:
        with self.page.expect_response(self._is_product_query):
            self.page.get_by_label(brand, exact=True).check()

    def select_for_comparison(self, *indexes: int) -> None:
        for i in indexes:
            self.compare_buttons.nth(i).click()
