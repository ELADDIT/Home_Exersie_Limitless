"""Account security: lockout after wrong passwords, changing a password, privacy of contact messages, and customers blocked from admin reports."""
import uuid

import pytest

from toolshop.data import strong_password

LOCK_AFTER_AT_MOST = 5  # observed on the live API: attempts 1-3 -> 401, attempt 4 -> 423


def login(api, email, password):
    return api.post("/users/login", json={"email": email, "password": password})


# ---- a. lockout ----------------------------------------------------------
@pytest.mark.progression
def test_repeated_wrong_passwords_lock_the_account(api, customer):
    statuses = [login(api, customer.email, customer.password + "x").status_code for _ in range(LOCK_AFTER_AT_MOST)]

    assert statuses[0] == 401, f"a first wrong password is a plain rejection: {statuses}"
    assert 423 in statuses, f"the account must lock within {LOCK_AFTER_AT_MOST} wrong attempts (brute-force protection): {statuses}"
    correct = login(api, customer.email, customer.password)
    assert correct.status_code == 423, \
        f"while locked even the correct password must be refused, otherwise a guesser still gets in: {correct.status_code} {correct.text}"
    assert "access_token" not in correct.text, "no token may be issued for a locked account"


# ---- b. change password --------------------------------------------------
def change_password(client, current, new, confirmation=None):
    return client.post("/users/change-password", json={
        "current_password": current, "new_password": new, "new_password_confirmation": confirmation or new})


@pytest.mark.progression
def test_changed_password_replaces_the_old_one(api, customer, customer_api):
    new_password = strong_password()

    r = change_password(customer_api, customer.password, new_password)

    assert r.status_code == 200, f"a valid change must succeed: {r.status_code} {r.text}"
    assert login(api, customer.email, customer.password).status_code == 401, "the OLD password must stop working"
    assert login(api, customer.email, new_password).status_code == 200, "the NEW password must work"


@pytest.mark.progression
def test_wrong_current_password_does_not_change_the_password(api, customer, customer_api):
    r = change_password(customer_api, customer.password + "x", strong_password())

    assert 400 <= r.status_code < 500, f"a wrong current password must be rejected: {r.status_code} {r.text}"
    assert login(api, customer.email, customer.password).status_code == 200, \
        "after a rejected change the original password must still work"


WEAK_PASSWORDS = [
    pytest.param("Ab1!", id="too-short"),
    pytest.param("password1!", id="no-uppercase"),
    pytest.param("PASSWORD1!", id="no-lowercase"),
    pytest.param("Password!!", id="no-digit"),
    pytest.param("Password11", id="no-symbol"),
]


@pytest.mark.progression
@pytest.mark.parametrize("weak", WEAK_PASSWORDS)
def test_weak_new_password_is_rejected(api, customer, customer_api, weak):
    r = change_password(customer_api, customer.password, weak)

    assert r.status_code == 422, f"a password that breaks the policy must be refused: {r.status_code} {r.text}"
    assert login(api, customer.email, weak).status_code == 401, "the weak password must not have been set"
    assert login(api, customer.email, customer.password).status_code == 200, "the old password must still work"


# ---- c. contact message privacy -----------------------------------------
@pytest.mark.progression
def test_customer_cannot_read_another_customers_contact_message(api, customer_api, other_customer):
    secret = f"private-{uuid.uuid4().hex}"
    sent = customer_api.post("/messages", json={"subject": "customer-service",
                                                "message": f"{secret} " + "please call me back about my order. " * 3})
    assert sent.status_code in (200, 201), f"Setup: contact message failed: {sent.status_code} {sent.text}"
    message_id = sent.json()["id"]
    other = api.as_token(api.login(other_customer.email, other_customer.password))

    direct = other.get(f"/messages/{message_id}")
    listing = other.get("/messages")

    assert secret not in direct.text, f"customer B read A's message text via the direct URL: {direct.status_code} {direct.text[:200]}"
    assert message_id not in listing.text and secret not in listing.text, "A's message leaked into B's message list"
    assert secret in customer_api.get(f"/messages/{message_id}").text, "Setup check: the owner must still see their own message"


# ---- d. admin reports ----------------------------------------------------
# GET /reports/* from the OpenAPI spec; the 2 already covered in test_access_control.py are left out.
REPORTS = [
    "/reports/total-sales-per-country",
    "/reports/top10-purchased-products",
    "/reports/top10-best-selling-categories",
    "/reports/average-sales-per-week?year=2024",
    "/reports/customers-by-country",
]


@pytest.mark.progression
@pytest.mark.parametrize("path", REPORTS, ids=[p.split("/")[-1].split("?")[0] for p in REPORTS])
def test_customer_cannot_read_admin_reports(customer_api, path):
    r = customer_api.get(path)

    assert r.status_code == 403, f"business reports are admin-only, a customer got {r.status_code}: {r.text[:150]}"
