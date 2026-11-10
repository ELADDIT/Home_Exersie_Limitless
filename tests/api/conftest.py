import pytest

from toolshop.data import Customer


@pytest.fixture
def other_customer(api) -> Customer:
    """A second fresh customer, used as 'somebody else' in privacy / access tests."""
    return api.register(Customer())


@pytest.fixture
def cart_with_items(customer_api, products) -> tuple[str, list[tuple[dict, int]]]:
    """A new cart owned by a fresh customer holding both catalog products (quantities 2 and 3)."""
    cart_id = customer_api.create_cart()
    lines = list(zip(products, (2, 3)))
    for product, qty in lines:
        customer_api.add_to_cart(cart_id, product["id"], qty)
    return cart_id, lines
