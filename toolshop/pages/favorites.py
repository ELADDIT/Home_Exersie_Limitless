from playwright.sync_api import Page


class FavoritesPage:
    def __init__(self, page: Page):
        self.page = page
        self.product_names = page.get_by_test_id("product-name")
