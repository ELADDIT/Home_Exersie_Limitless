"""Orders: the invoice total equals the sum of the cart lines, the order appears in the customer's own list, and nobody else can read it."""
import pytest

from toolshop.api.models import Cart, Invoice, InvoicePage


def place(customer_api, cart_id) -> Invoice:
    r = customer_api.place_order(cart_id)
    assert r.status_code == 201, f"order must be accepted: {r.status_code} {r.text}"
    return Invoice.model_validate(r.json())


def expected_total(customer_api, cart_id) -> float:
    cart = Cart.model_validate(customer_api.get(f"/carts/{cart_id}").json())
    return sum(i.product.price * i.quantity for i in cart.cart_items)


@pytest.mark.sanity
def test_order_total_equals_sum_of_lines(customer_api, customer, cart_with_items):
    cart_id, _ = cart_with_items
    expected = expected_total(customer_api, cart_id)

    invoice = place(customer_api, cart_id)

    assert invoice.user_id == customer.id, "the invoice must belong to the customer who ordered"
    assert invoice.total == pytest.approx(expected, abs=0.01), \
        f"invoice total {invoice.total} must equal sum of price*quantity {expected}"
    assert invoice.subtotal == pytest.approx(expected, abs=0.01)


@pytest.mark.progression
def test_order_appears_in_own_invoice_list_with_matching_lines(customer_api, cart_with_items):
    cart_id, lines = cart_with_items
    invoice = place(customer_api, cart_id)

    page = InvoicePage.model_validate(customer_api.get("/invoices").json())

    mine = next((i for i in page.data if i.id == invoice.id), None)
    assert mine is not None, "a placed order must show in the customer's invoice list"
    raw = next(i for i in customer_api.get("/invoices").json()["data"] if i["id"] == invoice.id)
    assert {l["product_id"]: l["quantity"] for l in raw["invoicelines"]} == {p["id"]: q for p, q in lines}, \
        "invoice lines must match what was in the cart"


@pytest.mark.sanity  # access control is risk #1: one privacy check runs on every push
def test_customer_cannot_read_another_customers_invoice(api, customer_api, other_customer, cart_with_items):
    invoice = place(customer_api, cart_with_items[0])
    other_token = api.login(other_customer.email, other_customer.password)
    other = api.as_token(other_token)

    direct = other.get(f"/invoices/{invoice.id}")
    listing = other.get("/invoices")

    assert direct.status_code == 404, f"customer B must not read A's invoice: {direct.status_code}"
    assert invoice.id not in {i["id"] for i in listing.json()["data"]}, "A's invoice leaked into B's list"


@pytest.mark.progression
def test_guest_cannot_read_an_invoice(api, customer_api, cart_with_items):
    invoice = place(customer_api, cart_with_items[0])

    assert api.get(f"/invoices/{invoice.id}").status_code == 401, "guests must log in to see invoices"
    assert api.get("/invoices").status_code == 401
