"""Catalog: product list shape, pagination, sorting, filtering by category/brand/price, search, and unknown ids."""
import pytest

from toolshop.api.models import Product, ProductPage


@pytest.fixture(scope="module")
def sample(api) -> Product:
    return ProductPage.model_validate(api.get("/products").json()).data[0]


@pytest.mark.progression
def test_pagination_meta_is_consistent(api):
    first = ProductPage.model_validate(api.get("/products", params={"page": 1}).json())
    last = ProductPage.model_validate(api.get("/products", params={"page": first.last_page}).json())

    assert first.current_page == 1 and len(first.data) == first.per_page
    assert first.last_page == -(-first.total // first.per_page), "last_page must be ceil(total / per_page)"
    assert len(last.data) == first.total - first.per_page * (first.last_page - 1), "last page holds the remainder"
    assert not {p.id for p in first.data} & {p.id for p in last.data}, "pages must not overlap"


@pytest.mark.progression
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_sort_by_price_is_ordered(api, direction):
    page = ProductPage.model_validate(api.get("/products", params={"sort": f"price,{direction}"}).json())

    prices = [p.price for p in page.data]
    assert prices == sorted(prices, reverse=direction == "desc"), f"prices not sorted {direction}: {prices}"


@pytest.mark.progression
def test_sort_by_name_ascending_is_ordered(api):
    page = ProductPage.model_validate(api.get("/products", params={"sort": "name,asc"}).json())

    names = [p.name.lower() for p in page.data]
    assert names == sorted(names), f"names not alphabetical: {names}"


@pytest.mark.progression
@pytest.mark.parametrize("kind", ["category", "brand"])
def test_filter_returns_only_matching_products(api, sample, kind):
    wanted = getattr(sample, kind).id

    page = ProductPage.model_validate(api.get("/products", params={f"by_{kind}": wanted}).json())

    assert page.data, f"filtering by a {kind} that has products must not be empty"
    assert all(getattr(p, kind).id == wanted for p in page.data), f"filter by {kind} leaked other {kind}s"


@pytest.mark.progression
def test_price_range_filter_is_respected(api):
    page = ProductPage.model_validate(api.get("/products", params={"between": "price,10,30"}).json())

    assert page.data
    assert all(10 <= p.price <= 30 for p in page.data), f"price outside 10-30: {[p.price for p in page.data]}"


@pytest.mark.progression
def test_search_returns_only_matching_names(api, sample):
    term = sample.name.split()[0]

    page = ProductPage.model_validate(api.get("/products/search", params={"q": term}).json())

    assert any(p.id == sample.id for p in page.data), "searching a product's own name must find it"
    assert all(term.lower() in p.name.lower() for p in page.data), f"results not matching '{term}'"


@pytest.mark.progression
def test_search_without_matches_is_empty(api):
    page = ProductPage.model_validate(api.get("/products/search", params={"q": "zzqqxxnomatch"}).json())

    assert page.total == 0 and page.data == [], "a nonsense query must return no products"


@pytest.mark.progression
def test_product_detail_matches_listing(api, sample):
    r = api.get(f"/products/{sample.id}")

    assert r.status_code == 200
    detail = Product.model_validate(r.json())
    assert (detail.id, detail.name, detail.price) == (sample.id, sample.name, sample.price), \
        "detail page must show the same product data as the list"


@pytest.mark.progression
def test_unknown_product_id_is_404(api):
    assert api.get("/products/does-not-exist").status_code == 404, "unknown product must be 'not found'"


def first_page_names(api) -> list[str]:
    return [p["name"] for p in api.get("/products", params={"page": 1}).json()["data"]]


@pytest.mark.progression
def test_every_product_can_be_found_by_its_full_name(api):
    names = [n for n in first_page_names(api) if " with " not in n.lower()]  # see the known bug below
    missing = [n for n in names
               if n not in {p["name"] for p in api.get("/products/search", params={"q": n}).json()["data"]}]
    assert not missing, f"customers can't find these products by their exact name: {missing}"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: search returns nothing for product names containing 'with', "
                                       "e.g. 'Claw Hammer with Shock Reduction Grip' (found 2026-11-10)")
def test_products_with_with_in_the_name_can_be_found(api):
    names = [n for n in first_page_names(api) if " with " in n.lower()]
    if not names:
        pytest.skip("no product name containing 'with' on the first catalog page")
    missing = [n for n in names
               if n not in {p["name"] for p in api.get("/products/search", params={"q": n}).json()["data"]}]
    assert not missing, f"customers can't find these products by their exact name: {missing}"
