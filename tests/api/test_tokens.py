"""Login token (JWT) handling: a stolen, forged or old token must not work."""
import base64
import json

import pytest


def b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def claims(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


@pytest.mark.progression
def test_token_is_short_lived_and_identifies_the_customer(customer):
    c = claims(customer.token)

    assert c["sub"] == customer.id, "the token must belong to the customer who logged in"
    assert c["role"] == "user"
    assert 0 < c["exp"] - c["iat"] <= 3600, f"a stolen token should expire quickly, lifetime is {c['exp'] - c['iat']} s"


@pytest.mark.progression
def test_token_with_edited_role_is_rejected(api, customer):
    header, _, signature = customer.token.split(".")
    forged = f"{header}.{b64({**claims(customer.token), 'role': 'admin'})}.{signature}"

    r = api.as_token(forged).get("/users")

    assert r.status_code == 401, f"a token whose payload was edited must be rejected: {r.status_code}"


@pytest.mark.progression
def test_unsigned_token_is_rejected(api, customer):
    forged = f"{b64({'typ': 'JWT', 'alg': 'none'})}.{b64({**claims(customer.token), 'role': 'admin'})}."

    r = api.as_token(forged).get("/users/me")

    assert r.status_code == 401, f"a token with alg=none must be rejected: {r.status_code}"


@pytest.mark.progression
def test_token_stops_working_after_logout(customer_api):
    assert customer_api.get("/users/logout").status_code == 200

    assert customer_api.get("/users/me").status_code == 401, "a logged-out token must not work any more"


@pytest.mark.progression
def test_old_token_stops_working_after_refresh(api, customer_api):
    r = customer_api.get("/users/refresh")
    assert r.status_code == 200
    new = api.as_token(r.json()["access_token"])

    assert customer_api.get("/users/me").status_code == 401, "the replaced token must not work any more"
    assert new.get("/users/me").status_code == 200, "the new token must work"
