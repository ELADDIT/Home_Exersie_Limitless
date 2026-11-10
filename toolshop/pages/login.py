from playwright.sync_api import Page


class LoginPage:
    def __init__(self, page: Page):
        self.page = page
        self.email = page.get_by_test_id("email")
        self.password = page.get_by_test_id("password")
        self.submit_button = page.get_by_test_id("login-submit")
        self.error = page.get_by_test_id("login-error")

    def login(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.submit_button.click()
