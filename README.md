# Toolshop test suite

Automated tests for [Toolshop](https://practicesoftwaretesting.com), a practice online hardware store with a web UI and a REST API. This repository holds the first version of its test suite.

**Dashboard (no login needed):** [eladdit.github.io/Home_Exersie_Limitless](https://eladdit.github.io/Home_Exersie_Limitless/)
The landing page shows the latest status of every test set and environment, a results-per-run chart, the failures in the latest runs, and the full run history. Filters: environment, test set, period. Each card links to the full Allure report of that run (steps, screenshots, request/response, trend graphs) and to the CI run.

| What | Where |
|---|---|
| Test plan (risks, scope, approach, *What changed*) | [TEST_PLAN.md](TEST_PLAN.md) |
| How to add a test (for new team members) | [docs/HOW_TO_ADD_A_TEST.md](docs/HOW_TO_ADD_A_TEST.md) |
| AI prompt log | [llm-log/](llm-log/) |
| Full AI conversation | [docs/ai-conversation.md](docs/ai-conversation.md) |

## The suite at a glance

| Set | Purpose | When it runs | API tests | UI tests | Runtime (4 workers) |
|---|---|---|---|---|---|
| **Sanity** | "Is the store fundamentally working?" Browse, login, cart, checkout, order totals | Every push | 4 | 3 | ~12 s |
| **Progression** | Features in depth: access control, validation edges, catalog, cart, orders, payments, tokens, a UI tour of the smaller features | Pull requests, pushes to `main`, nightly 02:00 UTC, on demand | 137 | 7 | ~50 s |

That is 10 UI tests in total (the brief allows 5–10). Some progression tests are marked **expected to fail**: each one is a confirmed bug in the app (see [Bugs found](#bugs-found-while-building)). They turn red automatically once the bug is fixed.

## Run it locally

Requires Python 3.12+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Admin credentials are never committed. The demo admin account is shown on the shop's login page.
export TOOLSHOP_ADMIN_EMAIL=...       # or put both in a local .env file (git-ignored)
export TOOLSHOP_ADMIN_PASSWORD=...

pytest -m sanity -n 4                 # sanity set only
pytest -m progression -n 4            # progression set only
pytest -n 4                           # everything
pytest --env with-bugs -m sanity -n 4 # another environment (prod is the default)
pytest tests/api/test_cart.py -k quantity   # one area while developing
```

To get an HTML report locally, add `--alluredir allure-results` and run `allure serve allure-results` ([Allure CLI](https://allurereport.org/docs/install/)).

**Environments:** `prod` (default) and `with-bugs` (a copy of the shop with deliberate bugs, so failures are expected there). To add one, put its URLs in `toolshop/config.py`, or set `TOOLSHOP_BASE_URL` and `TOOLSHOP_API_URL`.

## CI and dashboard

- `.github/workflows/sanity.yml` runs on every push, and `progression.yml` runs on PRs, `main`, nightly and on demand. Both call `_run-suite.yml`, and both can be started by hand with an environment choice (**Actions → Run workflow**).
- Tests run inside Microsoft's official Playwright container. Installing the browser took about 2 of the 5 allowed minutes, so the container saves most of that.
- The **nightly** run (02:00 UTC) runs both sets against **both environments** (`prod` and `with-bugs`).
- After each run on `main`, an Allure report is generated and published to GitHub Pages under `/<env>/<set>/`, together with a run log (`runs.json`: date, trigger, commit, counts, duration) that the landing dashboard reads. Each publish carries the previous run's Allure history forward. Runs for the same report are queued; different reports publish in parallel, and the push retries if another run got there first.
- The report sorts problems into categories. "Shared site slow or unreachable" (network timeouts, reported as **broken**) is kept separate from **failed** product checks and from known app bugs, so a red run says *what kind* of red it is.
- PR runs don't publish, so branches never pollute the team's history. Their raw results and Playwright traces are attached to the run as artifacts.

## Key design decisions

1. **API for the logic, browser for the journeys.** Rules, calculations, permissions and input combinations are tested through the API (fast, unlimited). The 10 browser tests cover what a customer must be able to do on screen, and each has a *mistake → error → fix → success* path.
2. **Every test creates its own customer.** The site is public and shared, and its demo accounts are used by strangers. A fresh customer per test (registered through the API, unique email) makes tests safe to run in parallel, several runs at a time. The demo admin is used for read-only checks only.
3. **In browser tests, the step under test is done only through the screen** (clicks and typing). The API is used only for preconditions, such as creating the customer, or as the source of the expected answer.
4. **Red must mean broken.** There are no sleeps; Playwright waits on what's visible. Selectors use the site's `data-test` attributes. Retries happen only on network errors to the shared site, never on a failed assertion. Known app bugs are strict `xfail`s, so a green run is honest and turns red once the bug is fixed.
5. **Orders are spread across the catalog.** Placing orders uses up real stock on the shared site. Order tests pick a random in-stock product and a random quantity of 1–3, never more than the real stock count (read via the admin API).
6. **Boundary values are tested** for every validated field: on the limit, just inside, just outside. Dates are computed from today so the tests never go stale.
7. **Easy to extend.** Shared code lives in `toolshop/` (config, API client, response models, page objects). Collection fails if a test has no `sanity`/`progression` marker, or if the suite exceeds 10 UI tests. See the [new-tester guide](docs/HOW_TO_ADD_A_TEST.md).
8. **Readable reports without per-test boilerplate.** One hook in `tests/conftest.py` gives every test a readable title, a description (its docstring, else its file's docstring), a product area (Checkout, Access control, …), a severity (sanity = blocker; security and money areas = critical), and tags (set, layer, `known-bug`). New tests get all of it automatically.
9. **Standard tools only:** pytest, pytest-playwright, pytest-xdist, requests, pydantic (response shapes), Faker, pytest-rerunfailures (network errors only), pytest-check (soft checks in the UI tour), Allure.

## Bugs found while building

All were confirmed by hand on 2026-11-10 and are covered by expected-to-fail tests, unless noted otherwise.

| Severity | Bug |
|---|---|
| Critical | Any logged-in customer can list **all users' personal data** (email, phone, address, date of birth) via `GET /users/search`. |
| Critical | A customer can change **another customer's order status** (`PUT /invoices/{id}/status`). |
| High | A customer can mark their **own** order as completed. |
| High | Catalog write endpoints (create/update products, brands, categories) **don't check for a login**: a guest gets "not found" or "invalid input" instead of 401. |
| Medium | A customer can read another customer's favorite. |
| Medium | Unknown payment methods (e.g. `"bitcoin"`, empty) are accepted as successful payments. |
| Medium | Registration accepts invalid emails such as `plainaddress`. |
| Medium | A customer whose 18th birthday is today can't register (off-by-one at the age limit). |
| Medium | The 99-per-line cart limit is only checked per request: adding 1 and then 99 gives a line of 100. |
| Known issue (no test) | **Invoice PDF is very slow:** after an order, "Download PDF" stays disabled for several minutes (more than 3 minutes in our timing). A test would have to wait longer than the whole 5-minute pipeline allows. We'd solve this differently: a separate scheduled check with a long timeout, or ask the team to expose the PDF job status so the test can wait on it efficiently. |
| Observation | The login token is stored in the browser's `localStorage`, so any script injected into the page could read it. |
| Observation | Invalid input often gets `404` instead of `422`; deleting someone else's favorite returns `204` although nothing is deleted. |
| Observation | A customer who opens `/admin/dashboard` lands on the login page with an empty header (looks like a silent logout). The compare selection persists across pages. |

## Directions I didn't finish

- **Script-injection test (token theft):** place an order whose billing street contains a harmless script, then check that the admin dashboard shows it as plain text. This is the realistic way a stolen admin token would happen. It was **left out on purpose**: on the shared demo site everyone would see that "street". It belongs in a private test environment.
- **Invoice PDF check:** see the known issue above.
- **Eco-friendly filter, sorting by name, pagination in the UI** aren't covered in the browser. Sorting and pagination are covered in the API.
- **Cross-browser and mobile layouts.** Only Chromium runs, to stay within the 5-minute budget.
- **Weaknesses I know about:**
  - **Shared-site dependency.** Strangers can lock the demo admin account with wrong passwords (the API locks an email after repeated failures), which would turn the admin-based tests red. The site's database is also reset now and then: product ids change, and stock and invoices start over. Our tests never rely on earlier data, but a reset in the middle of a run could fail a test.
  - **Tests consume shared stock.** This is mitigated, not solved: orders are spread out, and products run out between resets anyway.
  - The UI tests rely on a few product names (e.g. "Sledgehammer", "Thor Hammer") from the seed data.
  - The expected-to-fail tests for invalid emails create junk accounts on the shared site for as long as that bug exists.
- **Next steps:** run the suite against `with-bugs` on a schedule and compare it with prod; add contract tests generated from the OpenAPI spec; add a private environment (Docker image of Toolshop) for destructive and security tests.

## Time spent

About **2 hours** so far on 2026-11-10, starting at 12:15 Israel time:

- ~10 minutes reading the brief, looking at the site, and drafting the planning prompt with Gemini;
- the rest in one Claude Code session (from 12:25): planning, building, reviewing every test and screenshot, CI and the dashboard, and documentation.

This will be updated with the final total at submission.

## Notes and assumptions

- The shared site's database was reset between about **12:56 and 13:20 Israel time** (10:56–11:20 UTC) on 2026-11-10: invoice numbers restarted and product ids changed. No outage was seen.
- I assumed using the public demo admin account for **read-only** checks is acceptable, since the brief allows using anything the application offers.
- The brief PDF itself is not in the repository.
