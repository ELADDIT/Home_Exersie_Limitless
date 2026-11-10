import pytest

from toolshop.api.models import User
from toolshop.data import Customer


@pytest.mark.progression
def test_valid_registration_returns_user_without_password(api):
    c = Customer()

    r = api.post("/users/register", json=c.registration_payload())

    assert r.status_code == 201, f"valid registration must succeed: {r.status_code} {r.text}"
    user = User.model_validate(r.json())
    assert user.email == c.email and user.first_name == c.first_name
    assert c.password not in r.text and "password" not in r.json(), "the password must never be echoed back"
    assert api.login(c.email, c.password), "a newly registered customer must be able to log in"


@pytest.mark.progression
@pytest.mark.parametrize("field", ["first_name", "last_name", "email", "password"])
def test_registration_without_required_field_is_rejected(api, field):
    payload = Customer().registration_payload()
    payload.pop(field)

    r = api.post("/users/register", json=payload)

    assert r.status_code == 422, f"missing {field} must be rejected: {r.status_code} {r.text}"
    assert field in r.json(), f"the error must point at the missing field '{field}'"


@pytest.mark.progression
@pytest.mark.parametrize(
    "password, rule",
    [
        pytest.param("Ab1!", "at least 8", id="too-short"),
        pytest.param("abcdefg1!x", "uppercase and one lowercase", id="no-uppercase"),
        pytest.param("ABCDEFG1!X", "uppercase and one lowercase", id="no-lowercase"),
        pytest.param("Abcdefgh!x", "number", id="no-digit"),
        pytest.param("Abcdefg1xx", "symbol", id="no-symbol"),
    ],
)
def test_registration_enforces_password_policy(api, password, rule):
    payload = Customer(password=password).registration_payload()

    r = api.post("/users/register", json=payload)

    assert r.status_code == 422, f"weak password ({rule}) must be rejected: {r.status_code} {r.text}"
    assert rule in " ".join(r.json()["password"]), f"error should explain the violated rule '{rule}': {r.text}"


@pytest.mark.progression
def test_registration_with_existing_email_is_rejected_as_duplicate(api, customer):
    payload = Customer(email=customer.email).registration_payload()

    r = api.post("/users/register", json=payload)

    assert r.status_code == 409, f"an email can belong to only one account: {r.status_code} {r.text}"


@pytest.mark.progression
@pytest.mark.xfail(strict=True, reason="BUG: registration accepts syntactically invalid emails such as 'plainaddress' "
                                       "and returns 201 (found 2026-11-10)")
@pytest.mark.parametrize("email", ["plainaddress", "@no-local.com", "has space@x.com", "a@b"])
def test_registration_with_invalid_email_is_rejected(api, email):
    r = api.post("/users/register", json=Customer(email=email).registration_payload())

    assert r.status_code == 422, f"invalid email '{email}' must be rejected, got {r.status_code} {r.text}"
