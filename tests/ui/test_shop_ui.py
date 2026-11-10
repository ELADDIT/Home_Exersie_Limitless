"""Browser tests. Every step under test goes through the screen; the only API use is the
`customer` fixture, which creates a fresh account as a precondition."""
import re

import allure
import pytest
from playwright.sync_api import Page, expect

from toolshop.data import strong_password, unique_email
from toolshop.pages import (AccountPage, AdminDashboardPage, CheckoutPage, HeaderComponent, HomePage,
                            LoginPage, ProductPage, RegisterPage)


def money(text: str) -> float:
    return float(re.sub(r"[^0-9.]", "", text))


def add_product_from_home(page: Page, name: str, quantity: int = 1, expected_badge: str | None = None) -> None:
    """Open a product from the catalog, set the quantity with the + button, add it to the cart."""
    HomePage(page).open_product(name)
    product = ProductPage(page)
    for _ in range(quantity - 1):
        product.increase_quantity()
    expect(product.quantity).to_have_value(str(quantity))
    product.add_to_cart()
    expect(HeaderComponent(page).cart_badge).to_have_text(expected_badge or str(quantity))
    HeaderComponent(page).home_link.click()


# ---------------------------------------------------------------- SANITY
@pytest.mark.sanity
def test_guest_searches_and_adds_product_to_cart(page: Page):
    home, product, header, cart = HomePage(page), ProductPage(page), HeaderComponent(page), CheckoutPage(page)
    with allure.step("Search for a product by name"):
        home.open()
        home.search("Sledgehammer")
        expect(home.product_names).to_have_text(["Sledgehammer"])
    with allure.step("Open the product page and add 2 pieces to the cart"):
        home.open_product("Sledgehammer")
        expect(product.name).to_have_text("Sledgehammer")
        unit_price = money(product.unit_price.inner_text())
        product.increase_quantity()
        expect(product.quantity).to_have_value("2")
        product.add_to_cart()
    with allure.step("Header badge shows the quantity"):
        expect(header.cart_badge).to_have_text("2")
    with allure.step("Cart page shows the right product, quantity and line total"):
        header.open_cart()
        expect(cart.lines).to_have_count(1)
        expect(cart.line("Sledgehammer")).to_be_visible()
        expect(cart.line("Sledgehammer").get_by_test_id("product-quantity")).to_have_value("2")
        expect(cart.line_price("Sledgehammer")).to_have_text(f"${unit_price * 2:.2f}")
        expect(cart.cart_total).to_have_text(f"${unit_price * 2:.2f}")


@pytest.mark.sanity
def test_login_wrong_password_then_correct(page: Page, customer):
    header, login, account = HeaderComponent(page), LoginPage(page), AccountPage(page)
    with allure.step("Open the sign-in page and enter a wrong password"):
        HomePage(page).open()
        header.open_sign_in()
        login.login(customer.email, customer.password + "x")
        expect(login.error).to_have_text("Invalid email or password")
    with allure.step("Enter the correct password"):
        login.password.fill(customer.password)
        login.submit_button.click()
    with allure.step("Lands on the account page as the customer"):
        expect(page).to_have_url(re.compile(r"/account$"))
        expect(account.title).to_have_text("My account")
        expect(header.user_menu).to_have_text(f"{customer.first_name} {customer.last_name}")


@pytest.mark.sanity
def test_checkout_cash_on_delivery(page: Page, customer, pick_purchases):
    [(item, quantity)] = pick_purchases(1)  # random in-stock product, 1-3 units (orders use shared stock)
    header, cart = HeaderComponent(page), CheckoutPage(page)
    with allure.step("Add the picked product and quantity to the cart"):
        HomePage(page).open()
        add_product_from_home(page, item["name"], quantity)
    with allure.step("Cart -> sign in step: log in"):
        header.open_cart()
        cart.proceed_to_sign_in.click()
        cart.sign_in(customer.email, customer.password)
        expect(page.get_by_text(f"Hello {customer.first_name} {customer.last_name}, you are already logged in")).to_be_visible()
        cart.proceed_to_address.click()
    with allure.step("Billing address (NL, 1012AB, 8)"):
        cart.fill_address("NL", "1012AB", "8")
        expect(cart.city).to_have_value("Steensel")
        expect(cart.state).to_have_value("Noord-Holland")
        cart.proceed_to_payment.click()
    with allure.step("Pay on delivery and confirm"):
        cart.choose_payment("cash-on-delivery")
        cart.finish_button.click()
        expect(cart.payment_success).to_be_visible()
        cart.finish_button.click()
    with allure.step("Order confirmation with invoice number"):
        expect(cart.order_confirmation).to_contain_text("Your invoice number is INV-")


# ---------------------------------------------------------------- PROGRESSION
@pytest.mark.progression
def test_registration_invalid_then_valid(page: Page):
    reg = RegisterPage(page)
    email, password = unique_email(), strong_password()
    with allure.step("Submit the empty form: every required field shows an error"):
        reg.open()
        reg.submit()
        for name in ("first-name", "last-name", "dob", "country", "postal_code", "house_number",
                     "street", "city", "state", "phone", "email", "password"):
            expect(reg.error(name)).to_be_visible()
        expect(page).to_have_url(re.compile(r"/auth/register$"))
    with allure.step("Enter a weak password and a malformed email: errors name the problem"):
        reg.field("email").fill("not-an-email")
        reg.field("password").fill("abc")
        reg.submit()
        expect(reg.error("email")).to_have_text("Email format is invalid")
        expect(reg.error("password")).to_contain_text("minimal 6 characters")
    with allure.step("Fix every field and register once"):
        reg.fill_personal("Jane", "Tester", "1990-01-15", "0612345678", email, password)
        reg.fill_address("NL", "1012AB", "8")
        expect(reg.city).to_have_value("Steensel")
        reg.submit()
    with allure.step("Redirected to the login page"):
        expect(page).to_have_url(re.compile(r"/auth/login$"))
        expect(LoginPage(page).submit_button).to_be_visible()


@pytest.mark.progression
def test_checkout_credit_card_invalid_then_valid(page: Page, customer, pick_purchases):
    [(item, quantity)] = pick_purchases(1)  # random in-stock product, 1-3 units (orders use shared stock)
    header, cart = HeaderComponent(page), CheckoutPage(page)
    with allure.step("Add a product, sign in at checkout, enter the billing address"):
        HomePage(page).open()
        add_product_from_home(page, item["name"], quantity)
        header.open_cart()
        cart.proceed_to_sign_in.click()
        cart.sign_in(customer.email, customer.password)
        cart.proceed_to_address.click()
        cart.fill_address("NL", "1012AB", "8")
        expect(cart.city).to_have_value("Steensel")
        cart.proceed_to_payment.click()
    with allure.step("Credit card with bad number, expiry and CVV: errors shown, cannot confirm"):
        cart.choose_payment("credit-card")
        cart.fill_card("1234", "13/20", "1", "Jane Tester")
        expect(cart.card_error("Invalid card number format")).to_be_visible()
        expect(cart.card_error("Invalid date format")).to_be_visible()
        expect(cart.card_error("CVV must be 3 or 4 digits")).to_be_visible()
        expect(cart.finish_button).to_be_disabled()
    with allure.step("Fix the card details and pay once"):
        cart.fill_card("1234-1234-1234-1234", "12/2030", "123", "Jane Tester")
        expect(cart.card_error("Invalid")).to_have_count(0)
        expect(cart.finish_button).to_be_enabled()
        cart.finish_button.click()
        expect(cart.payment_success).to_be_visible()
        cart.finish_button.click()
    with allure.step("Order confirmation"):
        expect(cart.order_confirmation).to_contain_text("Your invoice number is INV-")


@pytest.mark.progression
def test_cart_quantity_change_and_remove(page: Page):
    header, cart = HeaderComponent(page), CheckoutPage(page)
    first, second = "Slip Joint Pliers", "Thor Hammer"
    with allure.step("Add two different products"):
        HomePage(page).open()
        add_product_from_home(page, first, 1, expected_badge="1")
        add_product_from_home(page, second, 1, expected_badge="2")
        header.open_cart()
        expect(cart.lines).to_have_count(2)
        price1, price2 = money(cart.unit_price(first).inner_text()), money(cart.unit_price(second).inner_text())
        expect(cart.cart_total).to_have_text(f"${price1 + price2:.2f}")
    with allure.step("Change the first quantity to 3: its line and the total recompute"):
        cart.set_quantity(first, 3)
        expect(cart.line_price(first)).to_have_text(f"${price1 * 3:.2f}")
        expect(cart.line_price(second)).to_have_text(f"${price2:.2f}")
        expect(cart.cart_total).to_have_text(f"${price1 * 3 + price2:.2f}")
    with allure.step("Remove the second product: only the first line and its total remain"):
        cart.remove(second)
        expect(cart.lines).to_have_count(1)
        expect(cart.line(second)).to_have_count(0)
        expect(cart.cart_total).to_have_text(f"${price1 * 3:.2f}")


@pytest.mark.progression
def test_catalog_filter_by_category_and_sort_by_price(page: Page):
    home = HomePage(page)
    with allure.step("Filter by the Hammer category"):
        home.open()
        home.filter_by_category("Hammer")
        expect(home.product_names.first).to_contain_text("ammer")
        expect(home.product_names.filter(has_not_text=re.compile("hammer", re.I))).to_have_count(0)
    with allure.step("Sort by price, low to high"):
        cheapest = min(home.displayed_prices())
        home.sort_by("Price (Low - High)")
        expect(home.product_prices.first).to_have_text(f"${cheapest:.2f}")  # waits for the re-render
        expect(home.product_names.filter(has_not_text=re.compile("hammer", re.I))).to_have_count(0)
        prices = home.displayed_prices()
        assert len(prices) > 1
        assert prices == sorted(prices), f"prices are not non-decreasing: {prices}"


@pytest.mark.progression
@pytest.mark.parametrize("role", ["customer", "admin"])
def test_access_control(page: Page, request, role):
    header, login = HeaderComponent(page), LoginPage(page)
    if role == "customer":
        customer = request.getfixturevalue("customer")
        email, password = customer.email, customer.password
    else:
        email, password = request.getfixturevalue("admin_credentials")
    with allure.step(f"Log in as {role} through the sign-in screen"):
        HomePage(page).open()
        header.open_sign_in()
        login.login(email, password)
        expect(header.user_menu).to_be_visible()
    with allure.step("Check which menu entries this role sees"):
        header.open_user_menu()
        if role == "customer":
            expect(header.my_account_entry).to_be_visible()
            expect(header.admin_dashboard_entry).to_have_count(0)
        else:
            expect(header.admin_dashboard_entry).to_be_visible()
    with allure.step("Open /admin/dashboard"):
        if role == "customer":
            page.goto("/admin/dashboard")
            expect(page).not_to_have_url(re.compile(r"/admin/dashboard"))
            expect(AdminDashboardPage(page).title).to_have_count(0)
        else:
            header.admin_dashboard_entry.click()
            expect(page).to_have_url(re.compile(r"/admin/dashboard$"))
            expect(AdminDashboardPage(page).title).to_have_text("Sales over the years")
