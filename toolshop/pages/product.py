from playwright.sync_api import Page


class ProductPage:
    def __init__(self, page: Page):
        self.page = page
        self.name = page.get_by_test_id("product-name")
        self.unit_price = page.get_by_test_id("unit-price")
        self.quantity = page.get_by_test_id("quantity")
        self.increase_button = page.get_by_test_id("increase-quantity")
        self.add_to_cart_button = page.get_by_test_id("add-to-cart")

    def increase_quantity(self) -> None:
        self.increase_button.click()

    def add_to_cart(self) -> None:
        self.add_to_cart_button.click()
