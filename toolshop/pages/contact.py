from playwright.sync_api import Page, expect

from .header import HeaderComponent
from .layout import expect_page_elements


class ContactPage:
    """Contact form. A guest fills in name and email; a logged-in customer does not (the shop takes them from the account)."""

    IDENTITY = [("First name field", "first-name"), ("Last name field", "last-name"), ("Email field", "email")]
    COMMON = [("Subject select", "subject"), ("Message field", "message"), ("Send button", "contact-submit")]
    EXPECTED_GUEST = [*IDENTITY, *COMMON]
    EXPECTED_LOGGED_IN = COMMON

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

    def expected(self) -> list[tuple[str, str]]:
        """Form fields for the current state: logged in (no name/email fields) or guest (all fields)."""
        header = HeaderComponent(self.page)
        header_elements = header.expected()  # waits until the header knows who is logged in
        if header.user_menu.is_visible():
            expect(self.first_name).to_be_hidden()  # the form first shows them, then hides them once the profile loaded
            return [*header_elements, *self.EXPECTED_LOGGED_IN]
        return [*header_elements, *self.EXPECTED_GUEST]

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Contact page", self.expected())

    def send(self, subject: str, message: str, first: str | None = None, last: str | None = None,
             email: str | None = None) -> None:
        """Fill and submit. Name and email are for guests only (a logged-in customer has no such fields)."""
        if first is not None:
            self.first_name.fill(first)
        if last is not None:
            self.last_name.fill(last)
        if email is not None:
            self.email.fill(email)
        self.subject.select_option(label=subject)
        self.message.fill(message)
        self.submit_button.click()
