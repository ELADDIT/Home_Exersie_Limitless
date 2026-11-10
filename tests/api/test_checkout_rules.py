"""Checkout rules: what may and may not become an order (empty cart, reuse, out of stock, billing address, guest), stock, payment methods and invoice line prices."""
import pytest

from toolshop.data import billing_payload

CARD = {"credit_card_number": "0000-0000-0000-0000", "expiration_date": "12/2030", "cvv": "123",
        "card_holder_name": "Jane Doe"}
BANK = {"bank_name": "Test Bank", "account_name": "Jane Doe", "account_number": "123456"}


def my_invoices(client) -> list[dict]:
    r = client.get("/invoices")
    assert r.status_code == 200, f"Setup: invoice list failed: {r.status_code} {r.text}"
    return r.json()["data"]


@pytest.fixture
def filled_cart(customer_api, pick_purchases) -> tuple[str, dict, int]:
    """A cart with one random in-stock product: (cart_id, product, quantity)."""
    cart_id = customer_api.create_cart()
    [(product, quantity)] = pick_purchases(1)
    customer_api.add_to_cart(cart_id, product["id"], quantity)
    return cart_id, product, quantity


@pytest.fixture(scope="session")
def out_of_stock_product(api) -> dict:
    """A purchasable-looking product the customer view marks out of stock (searched over the first catalog pages)."""
    page, last = 1, 1
    while page <= last and page <= 8:
        body = api.get("/products", params={"page": page}).json()
        last = body["last_page"]
        for p in body["data"]:
            if not p["in_stock"] and not p["is_rental"]:
                return p
        page += 1
    pytest.skip("no out-of-stock, non-rental product exists in the catalog right now")


# ---- a-c. orders that must be refused ------------------------------------
@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: POST /invoices accepts an EMPTY cart and creates an order with no "
                                       "items and total 0 (found 2026-11-10)")
def test_empty_cart_cannot_be_ordered(customer_api):
    cart_id = customer_api.create_cart()

    r = customer_api.place_order(cart_id)

    assert 400 <= r.status_code < 500, f"an empty cart must be rejected: {r.status_code} {r.text[:200]}"
    assert my_invoices(customer_api) == [], "a rejected order must not leave an invoice behind"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: the same cart can be ordered twice; both POST /invoices return 201 "
                                       "and two invoices exist (found 2026-11-10)")
def test_same_cart_cannot_be_ordered_twice(customer_api, filled_cart):
    cart_id, _, _ = filled_cart
    first = customer_api.place_order(cart_id)
    assert first.status_code == 201, f"Setup: first order failed: {first.status_code} {first.text}"

    second = customer_api.place_order(cart_id)

    assert 400 <= second.status_code < 500, f"re-submitting a used cart must be rejected: {second.status_code}"
    assert len(my_invoices(customer_api)) == 1, "one cart must produce exactly one invoice (double charge otherwise)"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: an out-of-stock product (e.g. Long Nose Pliers) can be added to a "
                                       "cart and ordered: POST /invoices returns 201 (found 2026-11-10)")
def test_out_of_stock_product_cannot_be_ordered(customer_api, out_of_stock_product):
    cart_id = customer_api.create_cart()
    customer_api.add_to_cart(cart_id, out_of_stock_product["id"], 1)

    r = customer_api.place_order(cart_id)

    assert 400 <= r.status_code < 500, f"selling something we do not have must be rejected: {r.status_code} {r.text[:200]}"
    assert my_invoices(customer_api) == [], "no invoice may exist for an out-of-stock product"


# ---- d. stock ------------------------------------------------------------
@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: ordering does not reduce stock; admin stock stays the same after a "
                                       "201 order, e.g. Hammer 24 -> 24 after 3 units (found 2026-11-10)")
def test_ordering_reduces_stock_by_the_ordered_quantity(customer_api, admin_api, filled_cart):
    cart_id, product, quantity = filled_cart
    before = admin_api.stock_level(product["id"])

    r = customer_api.place_order(cart_id)

    assert r.status_code == 201, f"Setup: order failed: {r.status_code} {r.text}"
    after = admin_api.stock_level(product["id"])
    # "<=": other shoppers on the shared site may buy the same product meanwhile
    assert after <= before - quantity, \
        f"stock of {product['name']} must drop by at least the {quantity} ordered, else we oversell: {before} -> {after}"


# ---- e. billing address --------------------------------------------------
def order_with(customer_api, cart_id, **changes):
    payload = billing_payload(cart_id)
    for key, value in changes.items():
        if value is None:
            payload.pop(key)
        else:
            payload[key] = value
    return customer_api.post("/invoices", json=payload)


@pytest.mark.progression
def test_city_not_in_country_is_rejected(customer_api, filled_cart):
    r = order_with(customer_api, filled_cart[0], billing_city="Nowhereville")

    assert r.status_code == 422, f"an address whose city is not in the country must be refused: {r.status_code} {r.text[:200]}"
    assert "billing_country" in r.json(), f"the error must point at billing_country: {r.text[:200]}"
    assert my_invoices(customer_api) == [], "a rejected address must not create an invoice"


BUG_OPTIONAL = "BUG: POST /invoices accepts a missing billing_{} (201) although the API spec marks it required (found 2026-11-10)"
REQUIRED_FIELDS = [
    pytest.param("street", id="street"),
    pytest.param("city", id="city"),
    pytest.param("state", id="state", marks=pytest.mark.xfail(strict=True, reason=BUG_OPTIONAL.format("state"))),
    pytest.param("country", id="country"),
    pytest.param("postal_code", id="postal_code",
                 marks=pytest.mark.xfail(strict=True, reason=BUG_OPTIONAL.format("postal_code"))),
]


@pytest.mark.progression
@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_missing_billing_field_is_rejected(customer_api, filled_cart, field):
    r = order_with(customer_api, filled_cart[0], **{f"billing_{field}": None})

    assert r.status_code == 422, f"an order without billing {field} must be refused: {r.status_code} {r.text[:200]}"
    assert f"billing_{field}" in r.json(), f"the error must name billing_{field}: {r.text[:200]}"
    assert my_invoices(customer_api) == [], "a rejected order must not create an invoice"


# ---- f. guest ------------------------------------------------------------
@pytest.mark.progression
def test_guest_cannot_place_an_order(api, customer_api, filled_cart):
    r = api.place_order(filled_cart[0])

    assert r.status_code == 401, f"ordering requires login: {r.status_code} {r.text[:200]}"
    assert my_invoices(customer_api) == [], "a guest request must not create an invoice for anyone"


# ---- g. payment methods --------------------------------------------------
PAYMENTS = [
    pytest.param("cash-on-delivery", {}, id="cash-on-delivery"),
    pytest.param("bank-transfer", BANK, id="bank-transfer"),
    pytest.param("buy-now-pay-later", {"monthly_installments": "6"}, id="buy-now-pay-later"),
    pytest.param("credit-card", CARD, id="credit-card"),
]


@pytest.mark.progression
@pytest.mark.parametrize("method, details", PAYMENTS)
def test_order_is_created_with_each_payment_method(customer_api, filled_cart, method, details):
    r = customer_api.place_order(filled_cart[0], method, details)

    assert r.status_code == 201, f"an order paid by {method} must be accepted: {r.status_code} {r.text[:200]}"
    stored = customer_api.get(f"/invoices/{r.json()['id']}")
    assert stored.status_code == 200, f"the new invoice must be readable: {stored.status_code}"
    assert stored.json()["payment"]["payment_method"] == method, \
        f"the invoice must record how the customer chose to pay: {stored.json().get('payment')}"


# ---- h. invoice lines ----------------------------------------------------
@pytest.mark.progression
def test_invoice_lines_use_unit_price_and_add_up_to_total(customer_api, cart_with_items):
    cart_id, lines = cart_with_items

    r = customer_api.place_order(cart_id)

    assert r.status_code == 201, f"Setup: order failed: {r.status_code} {r.text}"
    invoice = customer_api.get(f"/invoices/{r.json()['id']}").json()
    by_product = {l["product_id"]: l for l in invoice["invoicelines"]}
    assert set(by_product) == {p["id"] for p, _ in lines}, "the invoice must contain exactly the ordered products"
    for product, quantity in lines:
        line = by_product[product["id"]]
        assert line["unit_price"] == pytest.approx(product["price"]), \
            f"{product['name']}: the line must freeze the catalog price at order time"
        assert line["quantity"] == quantity
    line_sum = sum(l["unit_price"] * l["quantity"] for l in invoice["invoicelines"])
    assert invoice["total"] == pytest.approx(line_sum, abs=0.01), \
        f"the customer pays {invoice['total']} but the lines add up to {line_sum}"
