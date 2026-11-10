"""Boundary-value tests: each rule is checked on the limit, just inside and just outside.

Limits come from the API spec (maxLength / minLength) and the API's own error messages.
Dates are computed from today, so the tests never go stale.
"""
import datetime

import pytest

from toolshop.data import Customer


def years_ago(years: int, extra_days: int = 0) -> str:
    """Date `years` before today, shifted by `extra_days` (positive = further in the past).
    29 Feb maps to 28 Feb in non-leap years."""
    today = datetime.date.today()
    try:
        d = today.replace(year=today.year - years)
    except ValueError:
        d = today.replace(year=today.year - years, day=28)
    return str(d - datetime.timedelta(days=extra_days))


def register(api, **fields):
    """Register a fresh customer with some fields overridden. Keys like 'address.city' set nested fields."""
    payload = Customer().registration_payload()
    for key, value in fields.items():
        target = payload
        *parents, leaf = key.split(".")
        for p in parents:
            target = target[p]
        target[leaf] = value
    return api.post("/users/register", json=payload)


# ---- registration text fields: max length --------------------------------
LENGTH_LIMITS = [
    ("first_name", 40),
    ("last_name", 20),
    ("phone", 24),
    ("address.street", 70),
    ("address.house_number", 10),
    ("address.city", 40),
    ("address.state", 40),
]


@pytest.mark.progression
@pytest.mark.parametrize("field, limit", LENGTH_LIMITS, ids=[f for f, _ in LENGTH_LIMITS])
@pytest.mark.parametrize("delta, accepted", [(0, True), (-1, True), (1, False)], ids=["at-max", "max-minus-1", "max-plus-1"])
def test_registration_field_length_limits(api, field, limit, delta, accepted):
    value = "7" * (limit + delta)  # digits are valid for every text field incl. phone and house number

    r = register(api, **{field: value})

    if accepted:
        assert r.status_code == 201, f"{field} of {len(value)} chars (limit {limit}) must be accepted: {r.status_code} {r.text}"
    else:
        assert r.status_code == 422, f"{field} of {len(value)} chars (limit {limit}) must be rejected: {r.status_code} {r.text}"
        assert field in r.json(), f"the error must point at '{field}': {r.text}"


@pytest.mark.progression
@pytest.mark.parametrize("length, accepted", [(7, False), (8, True), (9, True)], ids=["7-chars", "8-chars-min", "9-chars"])
def test_password_minimum_length(api, length, accepted):
    password = ("Ab1$" + "x" * 20)[:length]  # always has upper, lower, digit and symbol

    r = register(api, password=password)

    expected = 201 if accepted else 422
    assert r.status_code == expected, f"password of {length} chars (min 8): expected {expected}, got {r.status_code} {r.text}"


# ---- date of birth: customers must be 18+ --------------------------------
@pytest.mark.progression
@pytest.mark.parametrize(
    "dob, accepted",
    [
        pytest.param(years_ago(18, extra_days=-1), False, id="turns-18-tomorrow"),
        pytest.param(years_ago(18, extra_days=1), True, id="turned-18-yesterday"),
        pytest.param(years_ago(30), True, id="age-30"),
        pytest.param(years_ago(-1), False, id="born-in-the-future"),
        pytest.param(years_ago(100), False, id="age-100"),
        pytest.param("1990-02-30", False, id="impossible-date"),
    ],
)
def test_date_of_birth_age_limits(api, dob, accepted):
    r = register(api, dob=dob)

    expected = 201 if accepted else 422
    assert r.status_code == expected, f"dob {dob}: expected {expected}, got {r.status_code} {r.text}"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: a customer whose 18th birthday is today is rejected "
                                       "('Customer must be 18 years old') - off-by-one at the age limit (found 2026-11-10)")
def test_customer_turning_18_today_can_register(api):
    r = register(api, dob=years_ago(18))

    assert r.status_code == 201, f"someone who is exactly 18 today is 18: {r.status_code} {r.text}"


# ---- cart quantity: 1..99 per line ---------------------------------------
@pytest.mark.progression
@pytest.mark.parametrize("quantity, accepted", [(1, True), (99, True), (100, False)], ids=["min-1", "max-99", "max-plus-1"])
def test_cart_quantity_limits_on_add(api, products, quantity, accepted):
    cart_id = api.create_cart()

    r = api.post(f"/carts/{cart_id}", json={"product_id": products[0]["id"], "quantity": quantity})

    lines = api.get(f"/carts/{cart_id}").json()["cart_items"]
    if accepted:
        assert r.status_code == 200, f"quantity {quantity} must be accepted: {r.status_code} {r.text}"
        assert [i["quantity"] for i in lines] == [quantity]
    else:
        assert 400 <= r.status_code < 500, f"quantity {quantity} must be rejected: {r.status_code} {r.text}"
        assert lines == [], "a rejected add must not create a cart line"


@pytest.mark.progression
@pytest.mark.parametrize("quantity, accepted", [(99, True), (100, False)], ids=["max-99", "max-plus-1"])
def test_cart_quantity_limits_on_update(api, products, quantity, accepted):
    cart_id, pid = api.create_cart(), products[0]["id"]
    api.add_to_cart(cart_id, pid, 1)

    r = api.put(f"/carts/{cart_id}/product/quantity", json={"product_id": pid, "quantity": quantity})

    final = api.get(f"/carts/{cart_id}").json()["cart_items"][0]["quantity"]
    if accepted:
        assert r.status_code == 200 and final == quantity, f"update to {quantity} must apply: {r.status_code} {r.text}"
    else:
        assert 400 <= r.status_code < 500, f"update to {quantity} must be rejected: {r.status_code} {r.text}"
        assert final == 1, "a rejected update must keep the old quantity"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: the 99-per-line limit is only checked per request; adding 1 then 99 "
                                       "gives a line of 100 (found 2026-11-10)")
def test_cart_line_cannot_exceed_99_by_adding_twice(api, products):
    cart_id, pid = api.create_cart(), products[0]["id"]
    api.add_to_cart(cart_id, pid, 1)

    api.post(f"/carts/{cart_id}", json={"product_id": pid, "quantity": 99})

    final = api.get(f"/carts/{cart_id}").json()["cart_items"][0]["quantity"]
    assert final <= 99, f"a cart line must never exceed 99 items, got {final}"
