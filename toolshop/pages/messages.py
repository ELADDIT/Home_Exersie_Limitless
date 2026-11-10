from playwright.sync_api import Locator, Page

from .header import HeaderComponent
from .layout import expect_page_elements


class MessagesPage:
    """My account -> Messages: the contact messages the logged-in customer has sent."""

    EXPECTED = [("Page title", "page-title"), ("Messages table", "text=Subject"), ("Status column", "text=Status")]

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")
        self.rows = page.locator("table tbody tr")

    def row_with(self, text: str) -> Locator:
        """The list row whose text contains `text` (the list shows only the start of each message)."""
        return self.rows.filter(has_text=text)

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Messages page", [*HeaderComponent(self.page).expected(), *self.EXPECTED])
