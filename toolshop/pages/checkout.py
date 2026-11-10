from playwright.sync_api import Locator, Page


class CheckoutPage:
    """Cart page and the checkout steps (cart, sign in, billing address, payment).

    All steps live on the same page; the step buttons are proceed-1/2/3 and finish.
    """

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

    # ---- cart ----
    def line(self, product_name: str) -> Locator:
        return self.lines.filter(has_text=product_name)

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
