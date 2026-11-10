from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class ProductPage:
    EXPECTED = [("Product name", "product-name"), ("Unit price", "unit-price"), ("Description", "product-description"),
                ("Quantity field", "quantity"), ("Decrease quantity button", "decrease-quantity"),
                ("Increase quantity button", "increase-quantity"), ("Add to cart button", "add-to-cart"),
                ("Add to favorites button", "add-to-favorites"), ("Compare button", "add-to-compare"),
                ("Specifications table", "product-specs")]

    def __init__(self, page: Page):
        self.page = page
        self.name = page.get_by_test_id("product-name")
        self.unit_price = page.get_by_test_id("unit-price")
        self.quantity = page.get_by_test_id("quantity")
        self.increase_button = page.get_by_test_id("increase-quantity")
        self.add_to_cart_button = page.get_by_test_id("add-to-cart")
        self.add_to_favorites_button = page.get_by_test_id("add-to-favorites")

    def expect_loaded(self, cart_filled: bool = False) -> None:
        expect_page_elements(self.page, "Product page", [*HeaderComponent(self.page).expected(cart_filled), *self.EXPECTED])

    def increase_quantity(self) -> None:
        self.increase_button.click()

    def add_to_cart(self) -> None:
        self.add_to_cart_button.click()

    def add_to_favorites(self) -> None:
        self.add_to_favorites_button.click()
