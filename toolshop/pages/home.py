from playwright.sync_api import Page, expect


class HomePage:
    """Catalog: search, category filter, sorting and product cards."""

    def __init__(self, page: Page):
        self.page = page
        self.search_input = page.get_by_test_id("search-query")
        self.search_button = page.get_by_test_id("search-submit")
        self.sort_select = page.get_by_test_id("sort")
        self.product_names = page.get_by_test_id("product-name")
        self.product_prices = page.get_by_test_id("product-price")

    @staticmethod
    def _is_product_query(response) -> bool:
        """The catalog is reloaded by one request to the product list (a QUERY call)."""
        return response.url.endswith("/products")

    def open(self) -> None:
        """Open the shop and wait until the catalog is on screen, like a user would before interacting.
        Without this, a search fired during the initial load gets overwritten when that load finishes."""
        self.page.goto("/")
        expect(self.product_names.first).to_be_visible()

    def search(self, text: str) -> None:
        with self.page.expect_response(lambda r: "/products/search" in r.url):
            self.search_input.fill(text)
            self.search_button.click()

    def open_product(self, name: str) -> None:
        self.product_names.filter(has_text=name).first.click()

    def filter_by_category(self, category: str) -> None:
        # the filter panel has no data-test per category label, so use the visible label text
        with self.page.expect_response(self._is_product_query):
            self.page.get_by_label(category, exact=True).check()

    def sort_by(self, label: str) -> None:
        with self.page.expect_response(self._is_product_query):
            self.sort_select.select_option(label=label)

    def displayed_prices(self) -> list[float]:
        return [float(t.lstrip("$")) for t in self.product_prices.all_inner_texts()]
