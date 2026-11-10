from playwright.sync_api import Page, expect

from .header import HeaderComponent
from .layout import expect_page_elements


class AdminDashboardPage:
    EXPECTED = [("Page title", "page-title"), ("Latest orders heading", "text=Latest orders")]

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")

    def expect_loaded(self) -> None:
        expect_page_elements(self.page, "Admin dashboard", [*HeaderComponent(self.page).expected(), *self.EXPECTED])


# Admin area: (menu entry data-test, URL path, page title, menu it lives in). Titles are what the site shows today.
ADMIN_PAGES = [
    ("nav-admin-dashboard", "/admin/dashboard", "Sales over the years", "user"),
    ("nav-admin-brands", "/admin/brands", "Brands", "user"),
    ("nav-admin-categories", "/admin/categories", "Categories", "user"),
    ("nav-admin-products", "/admin/products", "Products", "user"),
    ("nav-admin-orders", "/admin/orders", "Order", "user"),
    ("nav-admin-users", "/admin/users", "Users", "user"),
    ("nav-admin-messages", "/admin/messages", "Messages", "user"),
    ("nav-admin-settings", "/admin/settings", "Settings", "user"),
    ("nav-admin-statistics", "/admin/reports/statistics", "Statistics", "reports"),
]


class _AdminSearchPage:
    """An admin list page with a search box (orders, users)."""
    PREFIX = ""

    def __init__(self, page: Page):
        self.page = page
        self.title = page.get_by_test_id("page-title")
        self.search_input = page.get_by_test_id(f"{self.PREFIX}-search-query")
        self.search_button = page.get_by_test_id(f"{self.PREFIX}-search-submit")
        self.rows = page.locator("table tbody tr")

    def search(self, text: str) -> None:
        """Wait for the first list to load (a late first load would overwrite the search result), then search."""
        expect(self.rows.first).to_be_visible()
        with self.page.expect_response(lambda r: "/search" in r.url):
            self.search_input.fill(text)
            self.search_button.click()

    def row_with(self, text: str):
        return self.rows.filter(has_text=text)


class AdminOrdersPage(_AdminSearchPage):
    PREFIX = "order"


class AdminUsersPage(_AdminSearchPage):
    PREFIX = "user"


def open_admin_menu(page: Page, menu: str) -> None:
    """Admin entries live in the user menu; reports sit in its 'Reports' submenu (no data-test)."""
    page.get_by_test_id("nav-menu").click()
    if menu == "reports":
        # HOVER, don't click: on the real site clicking (or Enter/ArrowRight on) "Reports" closes the whole menu
        # (keyboard-accessibility bug), while hovering opens the submenu.
        page.get_by_role("button", name="Reports").hover()
