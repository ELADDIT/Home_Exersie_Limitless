from playwright.sync_api import Page

from .header import HeaderComponent
from .layout import expect_page_elements


class ContactPage:
    EXPECTED = [("First name field", "first-name"), ("Last name field", "last-name"), ("Email field", "email"),
                ("Subject select", "subject"), ("Message field", "message"), ("Send button", "contact-submit")]

    def __init__(self, page: Page):
        self.page = page
        self.first_name = page.get_by_test_id("first-name")
        self.last_name = page.get_by_test_id("last-name")
        self.email = page.get_by_test_id("email")
        self.subject = page.get_by_test_id("subject")
        self.message = page.get_by_test_id("message")
        self.submit_button = page.get_by_test_id("contact-submit")
        self.errors = page.locator("[data-test$='-error']")
        self.success = page.get_by_text("Thanks for your message!")

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Contact page", [*HeaderComponent(self.page).expected(), *self.EXPECTED])

    def send(self, first: str, last: str, email: str, subject: str, message: str) -> None:
        self.first_name.fill(first)
        self.last_name.fill(last)
        self.email.fill(email)
        self.subject.select_option(label=subject)
        self.message.fill(message)
        self.submit_button.click()
