"""Write-side access control: can a user CHANGE something that isn't theirs, or do admin-only actions?

Safety on the shared site: probes that SHOULD be blocked use non-existent ids or empty bodies, so even
when the app is broken nothing real is created or modified. Confirmed app bugs are strict xfails.
"""
import pytest

from toolshop.data import Customer

NO_SUCH_ID = "00000000000000000000000000"


@pytest.fixture
def placed_order(customer_api, pick_purchases) -> dict:
    """An order placed by the fresh `customer` (one random in-stock product, small quantity)."""
    cart_id = customer_api.create_cart()
    [(product, quantity)] = pick_purchases(1)
    customer_api.add_to_cart(cart_id, product["id"], quantity)
    r = customer_api.place_order(cart_id)
    assert r.status_code == 201, f"Setup: order failed: {r.status_code} {r.text}"
    return r.json()


def invoice_status(client, invoice_id) -> str:
    return client.get(f"/invoices/{invoice_id}").json()["status"]


# ---- another customer's data ---------------------------------------------
@pytest.mark.progression
def test_customer_cannot_edit_another_customers_profile(api, customer_api, other_customer):
    r = customer_api.request("PATCH", f"/users/{other_customer.id}", json={"first_name": "Hacked"})

    assert r.status_code in (403, 404), f"editing someone else's profile must be refused: {r.status_code} {r.text}"
    other = api.as_token(api.login(other_customer.email, other_customer.password))
    assert other.get("/users/me").json()["first_name"] == other_customer.first_name, "the victim's profile changed"


@pytest.mark.progression
def test_customer_cannot_delete_another_customer(api, customer_api, other_customer):
    r = customer_api.delete(f"/users/{other_customer.id}")

    assert r.status_code in (403, 404), f"deleting another account must be refused: {r.status_code} {r.text}"
    assert api.post("/users/login", json={"email": other_customer.email, "password": other_customer.password}).status_code == 200, \
        "the victim's account must still exist"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: customer B can change customer A's order status via "
                                       "PUT /invoices/{id}/status (found 2026-11-10)")
def test_customer_cannot_change_another_customers_order_status(api, customer_api, placed_order, other_customer):
    before = invoice_status(customer_api, placed_order["id"])
    other = api.as_token(api.login(other_customer.email, other_customer.password))

    r = other.put(f"/invoices/{placed_order['id']}/status", json={"status": "ON_HOLD", "status_message": "x"})

    assert invoice_status(customer_api, placed_order["id"]) == before, "another customer changed my order status"
    assert r.status_code in (403, 404), f"must be refused: {r.status_code} {r.text}"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: a customer can mark their own order COMPLETED via "
                                       "PUT /invoices/{id}/status, an admin-only action (found 2026-11-10)")
def test_customer_cannot_complete_own_order(customer_api, placed_order):
    r = customer_api.put(f"/invoices/{placed_order['id']}/status", json={"status": "COMPLETED"})

    assert invoice_status(customer_api, placed_order["id"]) != "COMPLETED", "customer completed their own order"
    assert r.status_code == 403, f"order status is an admin action: {r.status_code} {r.text}"


@pytest.mark.progression
def test_customer_cannot_delete_another_customers_favorite(api, customer_api, other_customer, products):
    fav = customer_api.post("/favorites", json={"product_id": products[0]["id"]})
    assert fav.status_code == 201, f"Setup: favorite failed: {fav.status_code} {fav.text}"
    other = api.as_token(api.login(other_customer.email, other_customer.password))

    other.delete(f"/favorites/{fav.json()['id']}")
    # Note: the API answers 204 here although nothing is deleted (misleading status, reported in README).

    assert fav.json()["id"] in {f["id"] for f in customer_api.get("/favorites").json()}, \
        "another customer deleted my favorite"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: customer B can read customer A's favorite via "
                                       "GET /favorites/{id} (found 2026-11-10)")
def test_customer_cannot_read_another_customers_favorite(api, customer_api, other_customer, products):
    fav = customer_api.post("/favorites", json={"product_id": products[0]["id"]}).json()
    other = api.as_token(api.login(other_customer.email, other_customer.password))

    r = other.get(f"/favorites/{fav['id']}")

    assert r.status_code in (403, 404), f"another customer's favorite must not be readable: {r.status_code} {r.text}"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: any customer can list ALL users with email, phone, address and "
                                       "date of birth via GET /users/search (found 2026-11-10)")
def test_customer_cannot_search_all_users(customer_api):
    r = customer_api.get("/users/search", params={"q": "a"})

    assert r.status_code == 403, f"user search is admin-only (personal data): {r.status_code} {r.text[:200]}"


# ---- privilege escalation ------------------------------------------------
@pytest.mark.progression
def test_registering_with_admin_role_does_not_grant_admin(api):
    c = Customer()
    payload = {**c.registration_payload(), "role": "admin"}
    assert api.post("/users/register", json=payload).status_code == 201

    me = api.as_token(api.login(c.email, c.password))

    assert me.get("/users").status_code == 403, "a self-declared 'admin' role must be ignored"


# ---- admin-only actions --------------------------------------------------
GUEST_WRITES = [
    pytest.param("PUT", f"/products/{NO_SUCH_ID}", id="update-product"),
    pytest.param("PATCH", f"/products/{NO_SUCH_ID}", id="patch-product"),
    pytest.param("PUT", f"/brands/{NO_SUCH_ID}", id="update-brand"),
    pytest.param("POST", "/brands", id="create-brand"),
    pytest.param("POST", "/categories", id="create-category"),
    pytest.param("POST", "/products", id="create-product"),
]


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: catalog write endpoints don't require login; a guest gets "
                                       "404/422 (input checked) instead of 401 (found 2026-11-10)")
@pytest.mark.parametrize("method, path", GUEST_WRITES)
def test_guest_cannot_write_catalog(api, method, path):
    r = api.request(method, path, json={})  # empty body + unknown id: nothing can be created or changed

    assert r.status_code == 401, f"guest {method} {path} must require login: {r.status_code} {r.text[:150]}"


@pytest.mark.progression
@pytest.mark.parametrize("path", [f"/products/{NO_SUCH_ID}", f"/brands/{NO_SUCH_ID}"], ids=["product", "brand"])
def test_customer_cannot_delete_catalog_items(customer_api, path):
    r = customer_api.delete(path)

    assert r.status_code == 403, f"deleting catalog items is admin-only: {r.status_code} {r.text}"
