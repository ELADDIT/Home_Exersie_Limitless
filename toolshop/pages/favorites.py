from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class FavoritesPage:
    EXPECTED = [("Page title", "page-title")]
    EXPECTED_WITH_ITEMS = [("Favorite product name", "product-name")]

    def __init__(self, page: Page):
        self.page = page
        self.product_names = page.get_by_test_id("product-name")

    def expect_loaded(self, has_items: bool = False) -> None:
        elements = [*self.EXPECTED, *(self.EXPECTED_WITH_ITEMS if has_items else [])]
        expect_page_elements(self.page, "Favorites page", [*HeaderComponent(self.page).expected(), *elements])
