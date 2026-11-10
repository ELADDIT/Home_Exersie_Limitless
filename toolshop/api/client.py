"""Thin wrapper around requests.Session for the Toolshop REST API.

- Low-level `get/post/put/delete` return the raw Response so tests assert status codes themselves.
- Domain helpers (`login`, `create_cart`, ...) assert their own success, because they are used
  for test setup and a broken precondition should fail loudly with a clear message.
- Every response is attached to the Allure report (method, URL, status, body).
- Transport retries use urllib3's standard Retry, only for idempotent GETs on gateway errors.
"""
import json

import allure
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from toolshop.data import Customer, billing_payload


def _attach_to_allure(response: requests.Response, *args, **kwargs) -> None:
    req = response.request
    body = req.body.decode() if isinstance(req.body, bytes) else (req.body or "")
    allure.attach(
        f"{req.method} {req.url}\n\nRequest body:\n{body}\n\n"
        f"Response {response.status_code}:\n{response.text[:5000]}",
        name=f"{req.method} {req.path_url} -> {response.status_code}",
        attachment_type=allure.attachment_type.TEXT,
    )


class ToolshopApi:
    def __init__(self, api_url: str, timeout: float = 15.0, token: str | None = None):
        self.api_url = api_url
        self.timeout = timeout
        self.token = token
        self.session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=(502, 503, 504),
                      allowed_methods=frozenset({"GET"}), raise_on_status=False)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers["Accept"] = "application/json"
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.hooks["response"].append(_attach_to_allure)

    def as_token(self, token: str | None) -> "ToolshopApi":
        """A new client acting as the given user (None = guest)."""
        return ToolshopApi(self.api_url, self.timeout, token)

    # ---- low level -------------------------------------------------------
    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, f"{self.api_url}{path}", **kwargs)

    def get(self, path: str, **kw) -> requests.Response:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> requests.Response:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw) -> requests.Response:
        return self.request("PUT", path, **kw)

    def delete(self, path: str, **kw) -> requests.Response:
        return self.request("DELETE", path, **kw)

    # ---- domain helpers (used for setup; assert their own success) ------
    def login(self, email: str, password: str) -> str:
        r = self.post("/users/login", json={"email": email, "password": password})
        assert r.status_code == 200, f"Setup: login failed for {email}: {r.status_code} {r.text}"
        return r.json()["access_token"]

    def register(self, customer: Customer) -> Customer:
        r = self.post("/users/register", json=customer.registration_payload())
        assert r.status_code == 201, f"Setup: registration failed: {r.status_code} {r.text}"
        customer.id = r.json()["id"]
        return customer

    def create_cart(self) -> str:
        r = self.post("/carts")
        assert r.status_code == 201, f"Setup: cart creation failed: {r.status_code} {r.text}"
        return r.json()["id"]

    def add_to_cart(self, cart_id: str, product_id: str, quantity: int = 1) -> None:
        r = self.post(f"/carts/{cart_id}", json={"product_id": product_id, "quantity": quantity})
        assert r.status_code == 200, f"Setup: add to cart failed: {r.status_code} {r.text}"

    def place_order(self, cart_id: str, payment_method: str = "cash-on-delivery",
                    payment_details: dict | None = None) -> requests.Response:
        return self.post("/invoices", json=billing_payload(cart_id, payment_method, payment_details))

    def in_stock_products(self, count: int = 2) -> list[dict]:
        """Purchasable products from the live catalog (ids differ between environments)."""
        r = self.get("/products", params={"page": 1})
        assert r.status_code == 200, f"Setup: product list failed: {r.status_code} {r.text}"
        items = [p for p in r.json()["data"] if p.get("in_stock") and not p.get("is_rental")]
        assert len(items) >= count, f"Setup: need {count} in-stock products, found {json.dumps(items)[:300]}"
        return items[:count]
