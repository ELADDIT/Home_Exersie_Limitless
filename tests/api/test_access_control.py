"""Read access by role: what a guest, a customer and an admin may see. Expected HTTP status per endpoint and role."""
import pytest

# (role, method path template) -> expected status. {other} = id of another customer.
ENDPOINTS = {
    "users-list": "/users",
    "me": "/users/me",
    "other-user": "/users/{other}",
    "invoices": "/invoices",
    "messages": "/messages",
    "sales-report": "/reports/total-sales-of-years",
    "monthly-report": "/reports/average-sales-per-month?year=2024",
}

EXPECTED = {
    "guest": {"users-list": 401, "me": 401, "other-user": 401, "invoices": 401, "messages": 401,
              "sales-report": 401, "monthly-report": 401},
    "customer": {"users-list": 403, "me": 200, "other-user": 404, "invoices": 200, "messages": 200,
                 "sales-report": 403, "monthly-report": 403},
    "admin": {"users-list": 200, "me": 200, "other-user": 200, "invoices": 200, "messages": 200,
              "sales-report": 200, "monthly-report": 200},
}

CASES = [pytest.param(role, ep, status, id=f"{role}-{ep}")
         for role, eps in EXPECTED.items() for ep, status in eps.items()]


@pytest.mark.progression
@pytest.mark.parametrize("role, endpoint, expected_status", CASES)
def test_endpoint_access_by_role(request, role, endpoint, expected_status, other_customer):
    client = {"guest": "api", "customer": "customer_api", "admin": "admin_api"}[role]
    client = request.getfixturevalue(client)

    r = client.get(ENDPOINTS[endpoint].format(other=other_customer.id))

    assert r.status_code == expected_status, (
        f"{role} calling GET {ENDPOINTS[endpoint]} should get {expected_status}, got {r.status_code} {r.text[:200]}")
