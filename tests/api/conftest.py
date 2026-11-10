import pytest

from toolshop.data import Customer


@pytest.fixture
def other_customer(api) -> Customer:
    """A second fresh customer, used as 'somebody else' in privacy / access tests."""
    return api.register(Customer())


@pytest.fixture
def cart_with_items(customer_api, pick_purchases) -> tuple[str, list[tuple[dict, int]]]:
    """A new cart for a fresh customer with 2 random in-stock products in small random quantities
    (bounded by real stock), so repeated runs don't drain one product on the shared site."""
    cart_id = customer_api.create_cart()
    lines = pick_purchases(2)
    for product, qty in lines:
        customer_api.add_to_cart(cart_id, product["id"], qty)
    return cart_id, lines
