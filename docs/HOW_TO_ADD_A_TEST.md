# How to add a test

This is for anyone joining the team. Read it once before your first test. It takes about 10 minutes.

## 1. Where things live

```
toolshop/                 shared code, no tests here
  config.py               environments (prod, with-bugs) and settings
  data.py                 test data builders (fresh customers, valid billing address)
  api/client.py           ToolshopApi: thin wrapper over requests
  api/models.py           pydantic models = expected shape of API responses
  pages/                  page objects for the UI (one class per page/component)
tests/
  conftest.py             shared fixtures: api, customer, customer_api, admin_api, products
  api/                    API tests, grouped by feature (test_cart.py, test_orders.py, ...)
  ui/                     browser tests (max 10 in total, see rule 3)
```

## 2. Choose the layer

| Question | Layer |
|---|---|
| Is it a business rule, a calculation, a validation, a permission, or an input combination? | **API** (`tests/api/`). Fast and unlimited. |
| Must a real user be able to do it on screen (a journey, a visible error)? | **UI** (`tests/ui/`). Slow and limited. Only when the API can't prove it. |

If both apply, put the input combinations in the API and add one UI journey.

## 3. The five rules

1. **Every test has exactly one set marker**: `@pytest.mark.sanity` (critical path, every push, must stay small) or `@pytest.mark.progression` (everything else). Collection fails if you forget it.
2. **Never use shared accounts for anything that changes state.** Use the `customer` fixture: it registers a brand-new customer for your test, which keeps parallel runs and other people on the public site from colliding. Admin (`admin_api`, `admin_credentials`) is **read-only**.
3. **The suite holds at most 10 UI test cases**, and every parametrized case counts. Collection fails above 10. To add one, argue for it in the PR or replace one.
4. **In UI tests, the step under test happens only through the screen** (click, type). Preconditions such as creating the customer may use the API. Each UI feature includes a *mistake → error → fix → success* path.
5. **No sleeps and no retries in tests.** Playwright's `expect(...)` waits by itself. The suite retries only on network errors to the shared site, never on a failed assertion.

## 4. Templates

**API test**

```python
import pytest
from toolshop.api.models import Cart

@pytest.mark.progression
@pytest.mark.parametrize("quantity", [1, 99], ids=["min", "max"])
def test_quantity_is_stored(api, products, quantity):
    cart_id = api.create_cart()                       # arrange (helpers assert their own success)

    r = api.post(f"/carts/{cart_id}", json={"product_id": products[0]["id"], "quantity": quantity})  # act

    assert r.status_code == 200, f"quantity {quantity} must be accepted: {r.text}"                   # assert
    cart = Cart.model_validate(api.get(f"/carts/{cart_id}").json())
    assert cart.cart_items[0].quantity == quantity
```

- Use `api` for a guest, `customer_api` for a fresh logged-in customer and `admin_api` for admin.
- Take product ids from the `products` fixture. Never hard-code ids: they differ between environments.
- Explain the business meaning in the assertion message. Someone reading the report at 2 a.m. should understand it.

**UI test**

```python
import allure
import pytest
from playwright.sync_api import Page, expect
from toolshop.pages import HeaderComponent, HomePage, LoginPage

@pytest.mark.progression
def test_something_a_user_does(page: Page, customer):      # `customer` = fresh account (API precondition)
    header, login = HeaderComponent(page), LoginPage(page)
    with allure.step("Open the shop and go to sign in"):
        HomePage(page).open()                               # waits until the catalog is on screen
        header.open_sign_in()
    with allure.step("Mistake first: wrong password shows an error"):
        login.login(customer.email, customer.password + "x")
        expect(login.error).to_be_visible()
    with allure.step("Fix it: correct password logs in"):
        login.login(customer.email, customer.password)
        expect(header.user_menu).to_contain_text(customer.first_name)
```

- Selectors: use `page.get_by_test_id("...")`, which reads the site's `data-test` attributes. Fall back to role or text, never XPath.
- Page objects contain *actions* (`login()`, `add_to_cart()`). Assertions stay in the test.

## 5. Known app bugs

If a correct assertion fails because the **app** is wrong, confirm it by hand first, then keep the correct assertion and mark it:

```python
@pytest.mark.xfail(strict=True, reason="BUG: <what is wrong> (found YYYY-MM-DD)")
```

`strict=True` makes the test go red once the bug is fixed, so someone removes the marker. Never loosen an assertion to make it pass.

## 6. Report labels come for free

Title, product area, severity and tags are set automatically in `tests/conftest.py`:
- **New test file:** add it to `FEATURE_BY_MODULE` so it lands in the right product area. Otherwise it shows up as "Other".
- **Docstring:** start the file with a one-line docstring saying what the area covers. It becomes the description of every test in the file.
- **Test names:** name the test as a sentence, e.g. `test_customer_cannot_read_another_customers_invoice`. The report title is built from it.
- **Don't rename tests casually:** the id (file, name and case) is what keeps a test's history together on the dashboard.

## 7. Run it

```bash
pytest tests/api/test_cart.py -k quantity    # one test while developing
pytest -m sanity -n 4                        # the sanity set
pytest -m progression -n 4                   # the progression set
pytest --env with-bugs -m sanity -n 4        # another environment
```

Run your new test **3 times** (`for i in 1 2 3; do pytest <your test> -n 4; done`) before opening a PR. A test that fails 1 time in 3 is worse than no test.

## 8. Review checklist (PR reviewers)

- [ ] Right layer (API unless the screen is the point)?
- [ ] Exactly one set marker; sanity only if it is truly critical-path?
- [ ] Fresh data (`customer`, new cart), no fixed emails or ids, safe to run 4× in parallel?
- [ ] Assertions check the business outcome (totals, ownership, state unchanged after a rejection), not just the status code?
- [ ] Assertion messages explain why it matters?
- [ ] UI: the step under test is done through the screen, includes a mistake → fix path, uses `data-test` selectors, has no sleeps?
- [ ] Passed 3 runs in a row?

## 9. Things about this shop that will bite you

- **Account lock:** after several failed logins, the API locks that email (HTTP 423). Only send wrong passwords for your own fresh `customer`, never a fixed email.
- **Orders use up real stock** on the shared site. Tests that place orders must use `pick_purchases(n)`: random in-stock products, quantity 1 to 3, capped by the real stock count.
- **Thor Hammer** has a limit of one per customer.
- **Billing address:** the city must match the country. Use `toolshop.data.BILLING_ADDRESS`.
- **The shared site's database gets reset now and then** (invoice numbers restart). Never rely on data created in an earlier run.
- **Wait for the page to be ready:** open the shop with `HomePage(page).open()`, which waits for the catalog. Typing into the search before the first load finishes gets overwritten.
