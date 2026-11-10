# UI test evidence (local run)

On GitHub-hosted runners the shop's Cloudflare bot check blocks the browser ("Performing security verification"). The UI tests are therefore skipped there as a **known issue** (blue, "Known issues" on the CI dashboard). See the main README.

These are the final screens of all 10 UI tests from a **local run on 2026-11-10 at about 14:30 Israel time**: `pytest tests/ui -n 4`, 10 passed in 21.7 s. Along the way, the journeys ran 54 page-element checks (every page they visit is checked for the elements a user needs).

| Test | Final screen |
|---|---|
| Guest searches and adds product to cart (sanity) | [png](guest-searches-and-adds-product-to-cart.png) |
| Login: wrong password, then correct (sanity) | [png](login-wrong-password-then-correct.png) |
| Checkout, cash on delivery (sanity) | [png](checkout-cash-on-delivery.png) |
| Registration: invalid, then valid | [png](registration-invalid-then-valid.png) |
| Checkout: invalid credit card, then valid | [png](checkout-credit-card-invalid-then-valid.png) |
| Cart: change quantity and remove | [png](cart-quantity-change-and-remove.png) |
| Catalog: filter by category, sort by price | [png](catalog-filter-by-category-and-sort-by-price.png) |
| Access control: customer | [png](access-control-customer.png) |
| Access control: admin | [png](access-control-admin.png) |
| Minor-features tour | [png](minor-features-tour.png) |
