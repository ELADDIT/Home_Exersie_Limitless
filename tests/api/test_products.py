"""Catalog sanity: the store lists products with valid data."""
import pytest

from toolshop.api.models import ProductPage


@pytest.mark.sanity
def test_product_catalog_lists_products(api):
    r = api.get("/products")

    assert r.status_code == 200
    page = ProductPage.model_validate(r.json())
    assert page.total > 0 and page.data, "catalog is empty"
    assert all(p.price > 0 for p in page.data), "every listed product must have a positive price"
