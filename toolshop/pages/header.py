from playwright.sync_api import Page, expect

from .layout import expect_page_elements


class HeaderComponent:
    """Top navigation bar, present on every page."""

    EXPECTED = [("Home link", "nav-home"), ("Categories menu", "nav-categories"), ("Contact link", "nav-contact"),
                ("Language select", "language-select")]
    CART_FILLED = [("Cart link", "nav-cart"), ("Cart badge", "cart-quantity")]  # only after something was added

    def __init__(self, page: Page):
        self.page = page
        self.sign_in_link = page.get_by_test_id("nav-sign-in")
        self.home_link = page.get_by_test_id("nav-home")
        self.cart_link = page.get_by_test_id("nav-cart")
        self.cart_badge = page.get_by_test_id("cart-quantity")
        self.user_menu = page.get_by_test_id("nav-menu")
        self.admin_dashboard_entry = page.get_by_test_id("nav-admin-dashboard")
        self.my_account_entry = page.get_by_test_id("nav-my-account")
        self.my_favorites_entry = page.get_by_test_id("nav-my-favorites")
        self.contact_link = page.get_by_test_id("nav-contact")
        self.categories_menu = page.get_by_test_id("nav-categories")
        self.rentals_link = page.get_by_test_id("nav-rentals")
        self.language_select = page.get_by_test_id("language-select")

    def expected(self, cart_filled: bool = False) -> list[tuple[str, str]]:
        """Header elements for the current state: "Sign in" when logged out, the user menu when logged in."""
        expect(self.sign_in_link.or_(self.user_menu)).to_be_visible()  # wait until the header knows who is logged in
        account = ("User menu", "nav-menu") if self.user_menu.is_visible() else ("Sign in link", "nav-sign-in")
        return [*self.EXPECTED, account, *(self.CART_FILLED if cart_filled else [])]

    def expect_loaded(self, cart_filled: bool = False) -> None:
        expect_page_elements(self.page, "Header", self.expected(cart_filled))

    def open_cart(self) -> None:
        self.cart_link.click()

    def open_sign_in(self) -> None:
        self.sign_in_link.click()

    def open_user_menu(self) -> None:
        self.user_menu.click()

    def switch_language(self, code: str) -> None:
        self.language_select.click()
        self.page.get_by_test_id(f"lang-{code}").click()

    def open_rentals(self) -> None:
        self.categories_menu.click()  # Rentals lives in the Categories dropdown
        self.rentals_link.click()
