from playwright.sync_api import Page


class AccountPage:
    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")
