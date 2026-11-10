import pytest

from toolshop.api.models import Cart


def get_cart(client, cart_id) -> Cart:
    r = client.get(f"/carts/{cart_id}")
    assert r.status_code == 200, f"cart must be readable: {r.status_code} {r.text}"
    return Cart.model_validate(r.json())


def quantities(cart: Cart) -> dict[str, int]:
    return {i.product_id: i.quantity for i in cart.cart_items}


@pytest.mark.sanity
def test_guest_can_create_cart_and_add_product(api, products):
    cart_id = api.create_cart()

    r = api.post(f"/carts/{cart_id}", json={"product_id": products[0]["id"], "quantity": 1})

    assert r.status_code == 200, f"adding a product to a cart must succeed: {r.status_code} {r.text}"
    assert quantities(get_cart(api, cart_id)) == {products[0]["id"]: 1}, "cart must contain exactly the added product"


@pytest.mark.progression
def test_update_quantity_changes_the_line(api, products):
    cart_id, pid = api.create_cart(), products[0]["id"]
    api.add_to_cart(cart_id, pid, 1)

    r = api.put(f"/carts/{cart_id}/product/quantity", json={"product_id": pid, "quantity": 5})

    assert r.status_code == 200, f"{r.status_code} {r.text}"
    assert quantities(get_cart(api, cart_id)) == {pid: 5}, "quantity must be replaced by the new value, not added"


@pytest.mark.progression
def test_delete_removes_only_that_line(api, products):
    cart_id = api.create_cart()
    for p in products:
        api.add_to_cart(cart_id, p["id"], 1)

    r = api.delete(f"/carts/{cart_id}/product/{products[0]['id']}")

    assert r.status_code == 204, f"{r.status_code} {r.text}"
    assert set(quantities(get_cart(api, cart_id))) == {products[1]["id"]}, "only the deleted product may disappear"


@pytest.mark.progression
def test_adding_same_product_twice_accumulates_quantity(api, products):
    cart_id, pid = api.create_cart(), products[0]["id"]

    api.add_to_cart(cart_id, pid, 1)
    api.add_to_cart(cart_id, pid, 2)

    cart = get_cart(api, cart_id)
    assert len(cart.cart_items) == 1, "the same product must stay on a single cart line"
    assert quantities(cart) == {pid: 3}, "adding again increases the existing line (1 + 2 = 3)"


@pytest.mark.progression
@pytest.mark.parametrize(
    "product, quantity",
    [
        pytest.param("valid", 0, id="zero-quantity"),
        pytest.param("valid", -1, id="negative-quantity"),
        pytest.param("valid", 100000, id="huge-quantity"),
        pytest.param("valid", "abc", id="non-numeric-quantity"),
        pytest.param("unknown", 1, id="unknown-product"),
    ],
)
def test_invalid_cart_input_is_rejected_and_cart_unchanged(api, products, product, quantity):
    cart_id = api.create_cart()
    api.add_to_cart(cart_id, products[1]["id"], 1)
    before = quantities(get_cart(api, cart_id))
    pid = products[0]["id"] if product == "valid" else "does-not-exist"

    r = api.post(f"/carts/{cart_id}", json={"product_id": pid, "quantity": quantity})

    assert 400 <= r.status_code < 500, f"invalid input must be rejected with a client error: {r.status_code} {r.text}"
    assert quantities(get_cart(api, cart_id)) == before, "a rejected request must not change the cart"


@pytest.mark.progression
@pytest.mark.parametrize("quantity", [0, -3], ids=["zero", "negative"])
def test_updating_to_invalid_quantity_is_rejected_and_cart_unchanged(api, products, quantity):
    cart_id, pid = api.create_cart(), products[0]["id"]
    api.add_to_cart(cart_id, pid, 2)

    r = api.put(f"/carts/{cart_id}/product/quantity", json={"product_id": pid, "quantity": quantity})

    assert 400 <= r.status_code < 500, f"{r.status_code} {r.text}"
    assert quantities(get_cart(api, cart_id)) == {pid: 2}, "a rejected update must keep the old quantity"
