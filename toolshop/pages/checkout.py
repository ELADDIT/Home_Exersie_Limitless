import re

from playwright.sync_api import Locator, Page

from .header import HeaderComponent
from .layout import expect_page_elements


class CheckoutPage:
    """Cart page and the checkout steps (cart, sign in, billing address, payment).

    All steps live on the same page; the step buttons are proceed-1/2/3 and finish.
    """

    EXPECTED_CART = [("Product name in cart", "product-title"), ("Quantity field", "product-quantity"),
                     ("Unit price", "product-price"), ("Line total", "line-price"), ("Cart total", "cart-total"),
                     ("Continue shopping button", "continue-shopping"), ("Proceed to checkout button", "proceed-1")]
    EXPECTED_SIGN_IN = [("Email field", "email"), ("Password field", "password"), ("Login button", "login-submit"),
                        ("Register link", "register-link"), ("Forgot password link", "forgot-password-link")]
    EXPECTED_SIGNED_IN = [("Already logged in message", "text=you are already logged in"),
                          ("Proceed to checkout button", "proceed-2")]
    EXPECTED_ADDRESS = [("Country select", "country"), ("Postal code field", "postal_code"),
                        ("House number field", "house_number"), ("Street field", "street"), ("City field", "city"),
                        ("State field", "state"), ("Proceed to checkout button", "proceed-3")]
    EXPECTED_PAYMENT = [("Payment method select", "payment-method"), ("Confirm/check payment button", "finish")]
    EXPECTED_CARD = [("Card number field", "credit_card_number"), ("Expiry date field", "expiration_date"),
                     ("CVV field", "cvv"), ("Card holder field", "card_holder_name")]  # only after choosing credit card
    EXPECTED_CONFIRMATION = [("Order confirmation message", "text=Thanks for your order!"),
                             ("Invoice number", "text=Your invoice number is")]

    def __init__(self, page: Page):
        self.page = page
        self.lines = page.locator("tr").filter(has=page.get_by_test_id("product-title"))
        self.cart_total = page.get_by_test_id("cart-total")
        self.proceed_to_sign_in = page.get_by_test_id("proceed-1")
        # sign in step
        self.email = page.get_by_test_id("email")
        self.password = page.get_by_test_id("password")
        self.login_button = page.get_by_test_id("login-submit")
        self.proceed_to_address = page.get_by_test_id("proceed-2")
        # billing address step
        self.country = page.get_by_test_id("country")
        self.postal_code = page.get_by_test_id("postal_code")
        self.house_number = page.get_by_test_id("house_number")
        self.street = page.get_by_test_id("street")
        self.city = page.get_by_test_id("city")
        self.state = page.get_by_test_id("state")
        self.proceed_to_payment = page.get_by_test_id("proceed-3")
        # payment step
        self.payment_method = page.get_by_test_id("payment-method")
        self.card_number = page.get_by_test_id("credit_card_number")
        self.card_expiry = page.get_by_test_id("expiration_date")
        self.card_cvv = page.get_by_test_id("cvv")
        self.card_holder = page.get_by_test_id("card_holder_name")
        self.finish_button = page.get_by_test_id("finish")
        self.payment_success = page.get_by_test_id("payment-success-message")
        self.order_confirmation = page.get_by_text("Thanks for your order!")

    def _expect(self, step: str, elements, cart_filled: bool = True) -> None:
        expect_page_elements(self.page, step, [*HeaderComponent(self.page).expected(cart_filled), *elements])

    def expect_cart_loaded(self) -> None:
        self._expect("Cart step", self.EXPECTED_CART)

    def expect_sign_in_loaded(self) -> None:
        self._expect("Sign-in step", self.EXPECTED_SIGN_IN)

    def expect_signed_in_loaded(self) -> None:
        self._expect("Sign-in step (logged in)", self.EXPECTED_SIGNED_IN)

    def expect_address_loaded(self) -> None:
        self._expect("Address step", self.EXPECTED_ADDRESS)

    def expect_payment_loaded(self, card: bool = False) -> None:
        self._expect("Payment step", [*self.EXPECTED_PAYMENT, *(self.EXPECTED_CARD if card else [])])

    def expect_confirmation_loaded(self) -> None:
        self._expect("Order confirmation", self.EXPECTED_CONFIRMATION, cart_filled=False)

    # ---- cart ----
    def line(self, product_name: str) -> Locator:
        """The cart line for exactly this product ("Hammer" must not match "Thor Hammer")."""
        exact = re.compile(rf"^\s*{re.escape(product_name)}\s*$")
        return self.lines.filter(has=self.page.get_by_test_id("product-title").filter(has_text=exact))

    def line_price(self, product_name: str) -> Locator:
        return self.line(product_name).get_by_test_id("line-price")

    def unit_price(self, product_name: str) -> Locator:
        return self.line(product_name).get_by_test_id("product-price")

    def set_quantity(self, product_name: str, quantity: int) -> None:
        field = self.line(product_name).get_by_test_id("product-quantity")
        field.fill(str(quantity))
        field.press("Tab")  # the cart recalculates on change, i.e. when the field loses focus

    def remove(self, product_name: str) -> None:
        self.line(product_name).locator("a.btn-danger").click()

    # ---- sign in ----
    def sign_in(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.login_button.click()

    # ---- billing address ----
    def fill_address(self, country: str, postal_code: str, house_number: str) -> None:
        """The app looks street, city and state up from the postcode and house number."""
        self.country.select_option(country)
        self.postal_code.fill(postal_code)
        self.house_number.fill(house_number)

    # ---- payment ----
    def choose_payment(self, value: str) -> None:
        self.payment_method.select_option(value)

    def fill_card(self, number: str, expiry: str, cvv: str, holder: str) -> None:
        self.card_number.fill(number)
        self.card_expiry.fill(expiry)
        self.card_cvv.fill(cvv)
        self.card_holder.fill(holder)
        self.card_holder.blur()

    def card_error(self, text: str) -> Locator:
        return self.page.locator(".alert-danger").filter(has_text=text)
