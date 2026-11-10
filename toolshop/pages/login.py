from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class LoginPage:
    EXPECTED = [("Email field", "email"), ("Password field", "password"), ("Login button", "login-submit"),
                ("Register link", "register-link"), ("Forgot password link", "forgot-password-link")]

    def __init__(self, page: Page):
        self.page = page
        self.email = page.get_by_test_id("email")
        self.password = page.get_by_test_id("password")
        self.submit_button = page.get_by_test_id("login-submit")
        self.error = page.get_by_test_id("login-error")

    def expect_loaded(self, cart_filled: bool = False) -> None:
        expect_page_elements(self.page, "Login page", [*HeaderComponent(self.page).expected(cart_filled), *self.EXPECTED])

    def login(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.submit_button.click()
