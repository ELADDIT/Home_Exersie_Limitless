"""Browser tests. Every step under test goes through the screen. The API is used only for preconditions
(a fresh customer, picking products from the live catalog, an existing order for the admin to find)."""
import re

import allure
import pytest
from playwright.sync_api import Page, expect
from pytest_check import check

from toolshop.data import strong_password, unique_email
from toolshop.pages import (ADMIN_PAGES, AccountPage, AdminDashboardPage, AdminOrdersPage, AdminUsersPage,
                            CheckoutPage, HeaderComponent, HomePage, InvoicesPage, LoginPage, ProductPage, RegisterPage,
                            open_admin_menu)


def money(text: str) -> float:
    return float(re.sub(r"[^0-9.]", "", text))


def add_product_from_home(page: Page, name: str, quantity: int = 1, expected_badge: str | None = None,
                          cart_filled: bool = False) -> None:
    """Open a product from the catalog, set the quantity with the + button, add it to the cart."""
    HomePage(page).open_product(name)
    product = ProductPage(page)
    product.expect_loaded(cart_filled=cart_filled)
    for _ in range(quantity - 1):
        product.increase_quantity()
    expect(product.quantity).to_have_value(str(quantity))
    product.add_to_cart()
    expect(HeaderComponent(page).cart_badge).to_have_text(expected_badge or str(quantity))
    HeaderComponent(page).home_link.click()
    HomePage(page).expect_loaded(cart_filled=True)


def check_invoice_in_my_invoices(page: Page, cart_total: str) -> None:
    """On the confirmation screen read the invoice number, then find exactly that invoice (and total) in My invoices."""
    confirmation = page.get_by_text(re.compile(r"Your invoice number is INV-\S+"))
    expect(confirmation).to_be_visible()
    invoice_number = re.search(r"INV-\S+", confirmation.inner_text()).group(0).rstrip(".")
    invoices = InvoicesPage(page)
    invoices.open_from_menu()
    expect(page).to_have_url(re.compile(r"/account/invoices$"))
    invoices.expect_loaded()
    expect(invoices.rows).to_have_count(1)  # a brand-new customer has exactly one invoice
    expect(invoices.row_with(invoice_number)).to_have_count(1)
    expect(invoices.row_with(invoice_number)).to_contain_text(cart_total)
    allure.attach(page.screenshot(), name="My invoices", attachment_type=allure.attachment_type.PNG)


# ---------------------------------------------------------------- SANITY
@pytest.mark.sanity
def test_guest_searches_and_adds_product_to_cart(page: Page, catalog_products):
    home, product, header, cart = HomePage(page), ProductPage(page), HeaderComponent(page), CheckoutPage(page)
    [item] = catalog_products(1)  # a random in-stock product from the live catalog
    name = item["name"]
    with allure.step(f"Search for '{name}' by name"):
        home.open()
        home.expect_loaded()
        home.search(name)
        expect(home.product_card_name(name)).to_have_count(1)
        expect(home.product_names.filter(has_not_text=re.compile(re.escape(name), re.I))).to_have_count(0)
    with allure.step("Open the product page and add 2 pieces to the cart"):
        home.open_product(name)
        expect(product.name).to_have_text(name)
        product.expect_loaded()
        unit_price = money(product.unit_price.inner_text())
        product.increase_quantity()
        expect(product.quantity).to_have_value("2")
        product.add_to_cart()
    with allure.step("Header badge shows the quantity"):
        expect(header.cart_badge).to_have_text("2")
    with allure.step("Cart page shows the right product, quantity and line total"):
        header.open_cart()
        cart.expect_cart_loaded()
        expect(cart.lines).to_have_count(1)
        expect(cart.line(name)).to_be_visible()
        expect(cart.line(name).get_by_test_id("product-quantity")).to_have_value("2")
        expect(cart.line_price(name)).to_have_text(f"${unit_price * 2:.2f}")
        expect(cart.cart_total).to_have_text(f"${unit_price * 2:.2f}")


@pytest.mark.sanity
def test_login_wrong_password_then_correct(page: Page, customer):
    header, login, account = HeaderComponent(page), LoginPage(page), AccountPage(page)
    with allure.step("Open the sign-in page and enter a wrong password"):
        home = HomePage(page)
        home.open()
        home.expect_loaded()
        header.open_sign_in()
        login.expect_loaded()
        login.login(customer.email, customer.password + "x")
        expect(login.error).to_have_text("Invalid email or password")
    with allure.step("Enter the correct password"):
        login.password.fill(customer.password)
        login.submit_button.click()
    with allure.step("Lands on the account page as the customer"):
        expect(page).to_have_url(re.compile(r"/account$"))
        expect(account.title).to_have_text("My account")
        account.expect_loaded()
        expect(header.user_menu).to_have_text(f"{customer.first_name} {customer.last_name}")


@pytest.mark.sanity
def test_checkout_cash_on_delivery(page: Page, customer, pick_purchases):
    [(item, quantity)] = pick_purchases(1)  # random in-stock product, 1-3 units (orders use shared stock)
    header, cart = HeaderComponent(page), CheckoutPage(page)
    with allure.step("Add the picked product and quantity to the cart"):
        home = HomePage(page)
        home.open()
        home.expect_loaded()
        add_product_from_home(page, item["name"], quantity)
    with allure.step("Cart -> sign in step: log in"):
        header.open_cart()
        cart.expect_cart_loaded()
        cart_total = cart.cart_total.inner_text()  # what the customer is about to pay, e.g. "$14.15"
        cart.proceed_to_sign_in.click()
        cart.expect_sign_in_loaded()
        cart.sign_in(customer.email, customer.password)
        expect(page.get_by_text(f"Hello {customer.first_name} {customer.last_name}, you are already logged in")).to_be_visible()
        cart.expect_signed_in_loaded()
        cart.proceed_to_address.click()
    with allure.step("Billing address (NL, 1012AB, 8)"):
        cart.expect_address_loaded()
        cart.fill_address("NL", "1012AB", "8")
        expect(cart.city).to_have_value("Steensel")
        expect(cart.state).to_have_value("Noord-Holland")
        cart.proceed_to_payment.click()
    with allure.step("Pay on delivery and confirm"):
        cart.expect_payment_loaded()
        cart.choose_payment("cash-on-delivery")
        cart.finish_button.click()
        expect(cart.payment_success).to_be_visible()
        cart.finish_button.click()
    with allure.step("Order confirmation with invoice number"):
        expect(cart.order_confirmation).to_contain_text("Your invoice number is INV-")
        cart.expect_confirmation_loaded()
    with allure.step("Open My account -> Invoices: the new invoice is listed with the total paid"):
        check_invoice_in_my_invoices(page, cart_total)


# ---------------------------------------------------------------- PROGRESSION
@pytest.mark.progression
def test_registration_invalid_then_valid(page: Page):
    reg = RegisterPage(page)
    email, password = unique_email(), strong_password()
    with allure.step("Submit the empty form: every required field shows an error"):
        reg.open()
        reg.expect_loaded()
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
        LoginPage(page).expect_loaded()


@pytest.mark.progression
def test_checkout_credit_card_invalid_then_valid(page: Page, customer, pick_purchases):
    [(item, quantity)] = pick_purchases(1)  # random in-stock product, 1-3 units (orders use shared stock)
    header, cart = HeaderComponent(page), CheckoutPage(page)
    with allure.step("Add a product, sign in at checkout, enter the billing address"):
        home = HomePage(page)
        home.open()
        home.expect_loaded()
        add_product_from_home(page, item["name"], quantity)
        header.open_cart()
        cart.expect_cart_loaded()
        cart_total = cart.cart_total.inner_text()  # what the customer is about to pay, e.g. "$14.15"
        cart.proceed_to_sign_in.click()
        cart.expect_sign_in_loaded()
        cart.sign_in(customer.email, customer.password)
        cart.expect_signed_in_loaded()
        cart.proceed_to_address.click()
        cart.expect_address_loaded()
        cart.fill_address("NL", "1012AB", "8")
        expect(cart.city).to_have_value("Steensel")
        cart.proceed_to_payment.click()
    with allure.step("Credit card with bad number, expiry and CVV: errors shown, cannot confirm"):
        cart.expect_payment_loaded()
        cart.choose_payment("credit-card")
        cart.expect_payment_loaded(card=True)
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
        cart.expect_confirmation_loaded()
    with allure.step("Open My account -> Invoices: the new invoice is listed with the total paid"):
        check_invoice_in_my_invoices(page, cart_total)


@pytest.mark.progression
def test_cart_quantity_change_and_remove(page: Page, catalog_products):
    header, cart = HeaderComponent(page), CheckoutPage(page)
    first, second = (p["name"] for p in catalog_products(2))  # two random in-stock products
    with allure.step("Add two different products"):
        home = HomePage(page)
        home.open()
        home.expect_loaded()
        add_product_from_home(page, first, 1, expected_badge="1")
        add_product_from_home(page, second, 1, expected_badge="2", cart_filled=True)
        header.open_cart()
        cart.expect_cart_loaded()
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
def test_catalog_filter_by_category_and_sort_by_price(page: Page, api):
    home = HomePage(page)
    # Precondition via API: a brand that really has Hammer products, so the combined result is not empty.
    hammer_id = next(c["id"] for c in api.get("/categories").json() if c["name"] == "Hammer")
    in_range = {"between": "price,1,100", "is_rental": "false", "by_category": hammer_id, "page": 1}
    hammers = api.get("/products", params=in_range).json()["data"]
    brands: dict[str, dict] = {}
    for p in hammers:
        brands.setdefault(p["brand"]["name"], p["brand"])
    brand = max(brands.values(), key=lambda b: sum(p["brand"]["id"] == b["id"] for p in hammers))
    allure.dynamic.parameter("brand", brand["name"])
    with allure.step("Filter by the Hammer category"):
        home.open()
        home.expect_loaded()
        home.filter_by_category("Hammer")
        expect(home.product_names.first).to_contain_text("ammer")
        expect(home.product_names.filter(has_not_text=re.compile("hammer", re.I))).to_have_count(0)
    with allure.step(f"Add the brand filter '{brand['name']}', lower the max price and sort by price, low to high"):
        home.filter_by_brand(brand["name"])
        max_price = home.lower_max_price(steps=3)
        home.sort_by("Price (Low - High)")
        expected = api.get("/products", params={**in_range, "by_brand": brand["id"], "between": f"price,1,{max_price}",
                                                "sort": "price,asc"}).json()["data"]
        assert expected, f"Setup: no {brand['name']} hammers up to ${max_price}"
        expect(home.product_names).to_have_count(len(expected))
    with allure.step("The screen shows exactly the API's list for the same filters, in price order"):
        # web-first: waits until the re-sorted list is rendered (the count alone is right before the order is)
        expect(home.product_names).to_have_text([p["name"] for p in expected])
        prices = home.displayed_prices()
        assert prices == [p["price"] for p in expected]
        assert prices == sorted(prices), f"prices are not non-decreasing: {prices}"
        assert all(p <= max_price for p in prices), f"price above {max_price} shown"
        expect(home.product_names.filter(has_not_text=re.compile("hammer", re.I))).to_have_count(0)
        allure.attach(page.screenshot(), name="Combined filters", attachment_type=allure.attachment_type.PNG)


@pytest.mark.progression
@pytest.mark.parametrize("role", ["customer", "admin"])
def test_access_control(page: Page, request, role):
    """Customer: no admin menu, and every admin page is refused when opened by URL.
    Admin: every admin page opens from the menu, and the admin can find a customer's account and order."""
    header, login = HeaderComponent(page), LoginPage(page)
    if role == "customer":
        customer = request.getfixturevalue("customer")
        email, password = customer.email, customer.password
    else:
        # Precondition via API: a fresh customer with one order, for the admin to find on screen.
        shopper, shopper_api = request.getfixturevalue("customer"), request.getfixturevalue("customer_api")
        cart_id = shopper_api.create_cart()
        [(product, quantity)] = request.getfixturevalue("pick_purchases")(1)
        shopper_api.add_to_cart(cart_id, product["id"], quantity)
        order = shopper_api.place_order(cart_id)
        assert order.status_code == 201, f"Setup: order failed: {order.status_code} {order.text}"
        invoice = order.json()
        email, password = request.getfixturevalue("admin_credentials")
    with allure.step(f"Log in as {role} through the sign-in screen"):
        home = HomePage(page)
        home.open()
        home.expect_loaded()
        header.open_sign_in()
        login.expect_loaded()
        login.login(email, password)
        expect(header.user_menu).to_be_visible()
    with allure.step("Check which menu entries this role sees"):
        if role == "customer":
            expect(page).to_have_url(re.compile(r"/account$"))
            AccountPage(page).expect_loaded()
        header.open_user_menu()
        if role == "customer":
            expect(header.my_account_entry).to_be_visible()
            expect(page.locator("[data-test^='nav-admin-']")).to_have_count(0)
        else:
            for menu_id, _, _, menu in ADMIN_PAGES:
                if menu == "user":
                    expect(page.get_by_test_id(menu_id)).to_be_visible()
            expect(page.get_by_role("button", name="Reports")).to_be_visible()
        header.open_user_menu()  # close it again
    if role == "customer":
        expect(page.get_by_role("button", name="Reports")).to_have_count(0)  # no reports submenu either
        for _, path, title, _ in ADMIN_PAGES:
            with check, allure.step(f"Customer opens {path} by URL: refused"):
                page.goto(path)
                expect(page).not_to_have_url(re.compile(re.escape(path) + "$"))
                expect(page.get_by_test_id("page-title").filter(has_text=title)).to_have_count(0)
        return
    for menu_id, path, title, menu in ADMIN_PAGES:
        with check, allure.step(f"Admin opens '{title}' from the menu"):
            open_admin_menu(page, menu)
            page.get_by_test_id(menu_id).click()
            expect(page).to_have_url(re.compile(re.escape(path) + "$"))
            expect(page.get_by_test_id("page-title")).to_have_text(title)
            if path == "/admin/dashboard":
                AdminDashboardPage(page).expect_loaded()
    with check, allure.step("Admin finds the customer's order (search by invoice number)"):
        header.open_user_menu()
        page.get_by_test_id("nav-admin-orders").click()
        orders = AdminOrdersPage(page)
        orders.search(invoice["invoice_number"])
        row = orders.row_with(invoice["invoice_number"])
        expect(row).to_have_count(1)
        expect(row).to_contain_text(f"{invoice['total']:.2f}")
    with check, allure.step("Admin finds the customer's account (search by email)"):
        header.open_user_menu()
        page.get_by_test_id("nav-admin-users").click()
        users = AdminUsersPage(page)
        users.search(shopper.email)
        row = users.row_with(shopper.email)
        expect(row).to_have_count(1)
        expect(row).to_contain_text(f"{shopper.first_name} {shopper.last_name}")
