from playwright.sync_api import Page


class ComparisonPage:
    def __init__(self, page: Page):
        self.page = page
        self.table = page.get_by_test_id("comparison-table")
        self.product_names = page.get_by_test_id("product-name")
