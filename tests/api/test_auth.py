import pytest

from toolshop.api.models import LoginToken, User


@pytest.mark.sanity
def test_fresh_customer_can_log_in_and_use_the_token(api, customer):
    r = api.post("/users/login", json={"email": customer.email, "password": customer.password})

    assert r.status_code == 200, f"A registered customer must be able to log in: {r.status_code} {r.text}"
    token = LoginToken.model_validate(r.json())
    assert token.access_token and token.expires_in > 0, "login must return a usable, expiring token"
    me = api.as_token(token.access_token).get("/users/me")
    assert me.status_code == 200, "the issued token must authenticate the customer"
    assert User.model_validate(me.json()).email == customer.email, "token must identify the customer who logged in"


@pytest.mark.progression
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"email": "{email}", "password": "WrongPassword1!"}, id="wrong-password"),
        pytest.param({"email": "nobody.{uuid}@example.com", "password": "Whatever123!"}, id="unknown-email"),
        pytest.param({"email": "", "password": ""}, id="empty-fields"),
        pytest.param({"email": "{email}", "password": ""}, id="empty-password"),
        pytest.param({}, id="no-fields"),
        # Unique per run: the API locks an identifier after repeated failed logins (HTTP 423),
        # so a fixed string would get locked by earlier/concurrent runs and fail for the wrong reason.
        pytest.param({"email": "not-an-email-{uuid}", "password": "Whatever123!"}, id="malformed-email"),
    ],
)
def test_login_with_bad_credentials_is_rejected_without_token(api, customer, payload):
    body = {k: v.format(email=customer.email, uuid=customer.id) for k, v in payload.items()}

    r = api.post("/users/login", json=body)

    assert r.status_code in (401, 422), f"Bad credentials must be rejected, got {r.status_code} {r.text}"
    assert "access_token" not in r.text, "a rejected login must never hand out a token"


@pytest.mark.progression
def test_login_error_does_not_reveal_whether_the_email_exists(api, customer):
    wrong_pw = api.post("/users/login", json={"email": customer.email, "password": "WrongPassword1!"})
    unknown = api.post("/users/login", json={"email": f"nobody.{customer.id}@example.com", "password": "WrongPassword1!"})

    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json(), "same error for wrong password and unknown user (no account enumeration)"
