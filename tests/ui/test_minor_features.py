"""UI/UX tour of the store's smaller features. A broken small feature is still a broken feature.

One test covers many features to stay within the 10-UI-test budget. Each feature is a soft check
(pytest-check): a failure is recorded and the tour continues, so one broken feature never hides
the state of the others. The report lists every failed step. Each step starts from a fresh page
so a failure can't leave the next step in a bad state.

Where the screen shows a filtered list, the expected products come from the API with the same
filter (the API is the oracle; the step under test is still done only through the screen).
"""
import re

import allure
import pytest
from playwright.sync_api import Page, expect
from pytest_check import check

from toolshop.data import unique_email
from toolshop.pages import (ComparisonPage, ContactPage, FavoritesPage, HeaderComponent, HomePage, LoginPage,
                            ProductPage, RentalsPage)

UI_DEFAULT_FILTER = {"between": "price,1,100", "is_rental": "false", "page": 1}  # what the shop page applies


def snap(page: Page, name: str) -> None:
    """Screenshot at the end of a step, so reviewers can see every feature in the report."""
    allure.attach(page.screenshot(), name=name, attachment_type=allure.attachment_type.PNG)


def api_product_names(api, **params) -> list[str]:
    r = api.get("/products", params={**UI_DEFAULT_FILTER, **params})
    assert r.status_code == 200, f"oracle lookup failed: {r.status_code}"
    return sorted(p["name"] for p in r.json()["data"])


@pytest.mark.progression
def test_minor_features_tour(page: Page, api, customer):
    home, header = HomePage(page), HeaderComponent(page)

    with check, allure.step("Price slider: lowering the max price shows exactly the products in range"):
        home.open()
        home.expect_loaded()
        max_price = home.lower_max_price(steps=3)
        expected = api_product_names(api, between=f"price,1,{max_price}")
        expect(home.product_names).to_have_count(len(expected))
        assert sorted(n.strip() for n in home.product_names.all_inner_texts()) == expected
        assert all(p <= max_price for p in home.displayed_prices()), f"price above {max_price} shown"
        snap(page, "Price slider")

    with check, allure.step("Brand filter: shows exactly that brand's products"):
        home.open()
        home.expect_loaded()
        brands = {b["name"]: b["id"] for b in api.get("/brands").json()}
        brand = sorted(brands)[0]
        home.filter_by_brand(brand)
        expected = api_product_names(api, by_brand=brands[brand])
        expect(home.product_names).to_have_count(len(expected))
        assert sorted(n.strip() for n in home.product_names.all_inner_texts()) == expected, f"brand filter '{brand}'"
        snap(page, "Brand filter")

    with check, allure.step("Compare: select 2 products, compare page shows both side by side"):
        home.open()
        home.expect_loaded()
        names = [n.strip() for n in home.product_names.all_inner_texts()[:2]]
        home.select_for_comparison(0, 1)
        expect(home.comparison_bar).to_contain_text("2 product(s) selected")
        home.compare_now_link.click()
        comparison = ComparisonPage(page)
        expect(comparison.table).to_be_visible()
        comparison.expect_loaded()
        expect(comparison.product_names).to_have_text(names)
        snap(page, "Compare")

    with check, allure.step("Language: switching to German translates the menu, and back to English"):
        home.open()
        home.expect_loaded()
        header.switch_language("de")
        expect(header.home_link).to_have_text(re.compile("Start"))
        expect(header.contact_link).to_have_text(re.compile("Kontakt"))
        header.switch_language("en")
        expect(header.contact_link).to_have_text(re.compile("Contact"))
        snap(page, "Language")

    with check, allure.step("Rentals: the rentals page lists rental products"):
        home.open()
        home.expect_loaded()
        header.open_rentals()
        expect(page).to_have_url(re.compile(r"/rentals$"))
        RentalsPage(page).expect_loaded()
        expect(page.get_by_test_id("page-title")).to_have_text(re.compile("Rentals"))
        rental_cards = page.locator("[data-test^='product-']")  # rental cards use product-<id>, not product-name
        expect(rental_cards.first).to_be_visible()
        expect(rental_cards.first).not_to_be_empty()
        snap(page, "Rentals")

    with check, allure.step("Contact form: empty submit shows errors, then a valid message is sent"):
        home.open()
        home.expect_loaded()
        header.contact_link.click()
        contact = ContactPage(page)
        contact.expect_loaded()
        contact.submit_button.click()
        expect(contact.errors).to_have_count(5)  # first name, last name, email, subject, message
        contact.send("Qa", "Automation", unique_email(), "Webmaster",
                     "Automated QA check of the contact form. Please ignore this message, thank you.")
        expect(contact.success).to_be_visible()
        snap(page, "Contact form")

    with check, allure.step("Favorites: a logged-in customer adds a product and finds it under My favorites"):
        home.open()
        home.expect_loaded()
        header.open_sign_in()
        LoginPage(page).expect_loaded()
        LoginPage(page).login(customer.email, customer.password)
        expect(header.user_menu).to_be_visible()
        home.open()
        home.expect_loaded()
        name = home.product_names.first.inner_text().strip()
        home.open_product(name)
        ProductPage(page).expect_loaded()
        ProductPage(page).add_to_favorites()
        expect(page.get_by_text("Product added to your favorites list.")).to_be_visible()
        header.open_user_menu()
        header.my_favorites_entry.click()
        expect(FavoritesPage(page).product_names).to_have_text([name])
        FavoritesPage(page).expect_loaded(has_items=True)
        snap(page, "Favorites")
