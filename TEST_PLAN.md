# Toolshop Test Plan

Application: https://practicesoftwaretesting.com (UI) and https://api.practicesoftwaretesting.com (REST API).
Roles that exist in the app: **guest** (not logged in), **customer**, **admin**.

## 1. Risks (ranked)

| # | Risk | Why it ranks here |
|---|------|-------------------|
| 1 | **Customers cannot complete a purchase** (cart → checkout → payment → order) | It is the store's revenue path. Any break here costs money directly and is visible to every customer. |
| 2 | **Broken authentication or access control**: login fails, a guest reaches protected data, a customer reaches admin functions or **another customer's invoices** | A security or privacy incident is worse than downtime. It also blocks risk 1 for logged-in customers. |
| 3 | **Wrong money in the cart or order**: line totals, cart total, quantity changes | Silent wrong totals erode trust and create refunds and support load. They are easy to miss by eye. |
| 4 | **Customers cannot find products**: search, category/brand filters, sorting, pagination, product page | If customers can't find a product, they can't buy it. Errors here are often partial (wrong order, a missing item) rather than total failures. |
| 5 | **Registration fails or accepts bad data** | New customers can't sign up, or invalid data reaches orders. Validation lives in both the UI and the API, so the two can drift apart. |
| 6 | Secondary features: favorites, contact form, language switch, product compare, rentals | Lower business impact. Covered lightly or not at all in this first version. |

## 2. Scope and layers

Guiding rule: **check business logic through the API** (fast, stable, no limit on count), and **use the browser only for what a real user must be able to do on screen**. The brief allows 5–10 UI tests, so UI tests cover journeys, not combinations of inputs.

| Area | API | UI | Reason |
|------|-----|----|--------|
| Checkout / orders (risk 1) | Create cart → add items → place order; check the order total equals the sum of its lines | Logged-in checkout from start to finish; payment error → fix → order placed | The money path must work through the screen, and the API checks the arithmetic precisely. |
| Auth and access control (risk 2) | Login inputs (valid, wrong password, unknown user, empty, malformed); a matrix of endpoint × role (guest/customer/admin → 401/403/200); customer A cannot read customer B's invoice | Wrong password → error → correct password → logged in; customer cannot open admin pages, admin can | The many combinations belong in the API. The UI checks that what a user can see and do matches their role. |
| Cart totals (risk 3) | Add, update quantity, remove; limits (0, negative, very large, unknown product) | Change quantity and remove an item → totals update on screen | The UI has to show what the API computed. |
| Catalog (risk 4) | Pagination, search, filter by category/brand, sort ascending/descending, 404 for unknown IDs, response shape | Guest search → product page → add to cart; filter + sort | The API checks correctness across many inputs; one UI test checks the controls work. |
| Registration (risk 5) | Required fields, invalid email, weak password, duplicate email | Submit empty or invalid form → errors shown → fix → registered | One UI journey; the validation combinations run in the API. |

**Test sets**

- **Sanity** (every push, about 1–2 minutes): the critical path of risks 1–3. That is product list, login, cart, and placing an order through the API, plus three UI journeys: browse & add to cart, login, checkout.
- **Progression** (pull requests, nightly, on demand): everything else above.

**UI budget: 9 of the 10 allowed tests**, with 1 kept in reserve.

- Sanity: 3 tests.
- Progression: 6 tests (registration, payment error and fix, cart update, filter and sort, access control × 2 roles).

## 3. Out of scope (deliberately)

- **Load and performance tests.** The brief forbids them, and the service is shared.
- **Admin changes to the shared catalog** (creating or deleting products, brands, categories). Other people use the same data, and a failed cleanup would affect them.
- **Visual and pixel comparison, cross-browser, mobile.** Chromium only, to stay within the 5-minute pipeline. This is a reasonable next step.
- **PDF invoice download, file attachments on messages, TOTP/2FA, reports and dashboards.** Lower risk for a first version.
- **Changing passwords on demo accounts.** It would break the accounts for everyone else.

## 4. Approach

- **Stack:**
  - Python 3 + **pytest**.
  - **pytest-playwright** (Chromium) for the UI, **requests** for the API.
  - **pydantic** models to check response shapes, **faker** for test data.
  - **pytest-xdist** (`-n 4`) for parallel runs, **allure-pytest** for reporting.
  - These are standard libraries, so there is no custom runner, retry logic or assertion code.
- **Parallel-safe test data:**
  - Every test that changes state registers its **own fresh customer** through the API (unique email per test). The shared demo customer accounts are never used for carts, orders or passwords, so concurrent runs (ours or other people's) can't collide.
  - The demo admin account is used for **read-only** access checks only.
- **UI tests use the screen for the step under test.** Preconditions (creating the fresh user) are done through the API to save time. The action being tested is always done by clicking and typing, and each UI feature includes a mistake-then-fix path.
- **Multiple environments:**
  - URLs come from environment variables or `--env` (`prod`, `with-bugs`); nothing is hard-coded in tests.
  - `with-bugs.practicesoftwaretesting.com` is the second environment. The suite is expected to fail there, which shows it catches real bugs.
- **A result you can trust:**
  - No fixed sleeps. Playwright's auto-waiting assertions, and `data-test` selectors only.
  - Retries happen **only** on network errors (connection, timeout), never on a failed assertion.
  - A failure always comes with a trace, a screenshot and the request/response in the report.
- **Secrets:** admin credentials are stored as GitHub Actions secrets and local environment variables, never in the repo.
- **CI and dashboard:**
  - GitHub Actions, with separate sanity and progression workflows.
  - An Allure report on GitHub Pages, with history kept across runs for trend charts. Anyone can open it without logging in.
- **Extensibility:** tests are grouped by feature (`tests/api/`, `tests/ui/`), with page objects for the UI and one shared API client. A test joins a set by adding a marker (`@pytest.mark.sanity` or `@pytest.mark.progression`).

---

## What changed

*Added after building. The plan above is the original, committed before any test code.*

1. **Boundary values got their own set, and validation moved up the risk ranking.** The original plan only had "invalid input" combinations. Exploring the API showed hard limits on almost every field (name lengths, password length, age 18–75, cart quantity 1–99). Testing each limit (on it, just inside, just outside) found two real bugs: someone turning 18 today can't register, and a cart line can exceed 99 by adding twice. **New ranking:** checkout → auth/access → money → *input validation at the edges* → catalog search. Wrong ages and quantities matter more than search order.
2. **Access control grew from "can I read it?" to "can I change it?" and "can I fake who I am?".** The first matrix only checked reads by role. Adding write-side checks (changing another customer's order, catalog writes as a guest) and token checks (edited, unsigned, logged-out and replaced tokens) found the most serious bugs in the shop: any customer can read all users' personal data and change anyone's order status.
3. **Test data had to respect the shared site's limits.** Three things only showed up while building:
   - the API **locks an email after repeated failed logins**, so fixed "wrong" emails got locked and caused false failures;
   - **orders consume real stock**: our order tests drained the first two products;
   - the site's **database gets reset**, which changes product ids.

   **Response:** every identifier is unique per run, orders pick a random in-stock product and a quantity of 1–3 capped by the real stock count, and no test relies on a hard-coded id.
4. **The 10th UI test** was kept in reserve, then used for a **tour of the smaller features** (price slider, brand filter, compare, language, rentals, contact form, favorites). A broken small feature is still a broken feature. Soft checks (`pytest-check`) record every failing feature instead of stopping at the first one. The tour stays within the 10-test budget.
5. **The invoice PDF came back into scope, and then went to "known issues".** It was out of scope in the original plan. During review we decided a customer's order confirmation PDF matters and should be checked in a UI test. Measuring it showed the PDF takes several minutes to be ready, more than the whole 5-minute pipeline, so it is documented as a known issue instead (see the README).
6. **CI runs in the official Playwright container.** The first run spent ~2 of the 5 allowed minutes installing the browser. Playwright was pinned to the container's version (1.64.1).
7. **A race condition in the shop's UI shaped how the tests wait.** Typing into the search while the first product list is still loading gets overwritten when that load finishes. The tests now wait for the catalog to be on screen first, as a person would. Likewise, each price-slider step waits for its own reload.
8. **Kept out on purpose:** a script-injection test on the admin dashboard (token theft). The probe would be visible to everyone on the shared demo, so it belongs in a private environment.
