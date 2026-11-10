from playwright.sync_api import Page


class RegisterPage:
    FIELDS = ("first-name", "last-name", "dob", "phone", "email", "password")

    def __init__(self, page: Page):
        self.page = page
        self.submit_button = page.get_by_test_id("register-submit")
        self.country = page.get_by_test_id("country")
        self.postal_code = page.get_by_test_id("postal_code")
        self.house_number = page.get_by_test_id("house_number")
        self.street = page.get_by_test_id("street")
        self.city = page.get_by_test_id("city")
        self.state = page.get_by_test_id("state")

    def field(self, name: str):
        return self.page.get_by_test_id(name)

    def error(self, name: str):
        return self.page.get_by_test_id(f"{name}-error")

    def open(self) -> None:
        self.page.goto("/auth/register")

    def submit(self) -> None:
        self.submit_button.click()

    def fill_personal(self, first_name: str, last_name: str, dob: str, phone: str, email: str, password: str) -> None:
        for name, value in zip(self.FIELDS, (first_name, last_name, dob, phone, email, password)):
            self.field(name).fill(value)

    def fill_address(self, country: str, postal_code: str, house_number: str) -> None:
        """The app looks street, city and state up from the postcode and house number."""
        self.country.select_option(country)
        self.postal_code.fill(postal_code)
        self.house_number.fill(house_number)
