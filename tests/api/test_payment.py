import pytest

CARD = {"credit_card_number": "0000-0000-0000-0000", "expiration_date": "12/2030", "cvv": "123",
        "card_holder_name": "Jane Doe"}
BANK = {"bank_name": "Test Bank", "account_name": "Jane Doe", "account_number": "123456"}
BUG_UNKNOWN_METHOD = "BUG: payment/check approves an unknown/empty payment method with 'Payment was successful' (found 2026-11-10)"

ACCEPTED = [
    pytest.param("cash-on-delivery", {}, id="cash-on-delivery"),
    pytest.param("bank-transfer", BANK, id="bank-transfer"),
    pytest.param("buy-now-pay-later", {"monthly_installments": "6"}, id="buy-now-pay-later"),
    pytest.param("credit-card", CARD, id="credit-card"),
]
REJECTED = [
    pytest.param("credit-card", {**CARD, "credit_card_number": "1"}, id="credit-card-bad-number"),
    pytest.param("credit-card", {}, id="credit-card-no-details"),
    pytest.param("bank-transfer", {}, id="bank-transfer-no-details"),
    pytest.param("buy-now-pay-later", {}, id="bnpl-no-installments"),
    pytest.param("gift-card", {"gift_card_number": "1", "validation_code": "1"}, id="gift-card-short-numbers"),
    pytest.param("gift-card", {}, id="gift-card-no-details"),
    pytest.param("bitcoin", {}, id="unknown-method-bitcoin",
                 marks=pytest.mark.xfail(strict=True, reason=BUG_UNKNOWN_METHOD)),
    pytest.param("", {}, id="empty-method",
                 marks=pytest.mark.xfail(strict=True, reason=BUG_UNKNOWN_METHOD)),
]


@pytest.mark.progression
@pytest.mark.parametrize("method, details", ACCEPTED)
def test_valid_payment_is_accepted(api, method, details):
    r = api.post("/payment/check", json={"payment_method": method, "payment_details": details})

    assert r.status_code == 200, f"valid {method} payment must be accepted: {r.status_code} {r.text}"
    assert r.json()["message"] == "Payment was successful"


@pytest.mark.progression
@pytest.mark.parametrize("method, details", REJECTED)
def test_invalid_payment_is_rejected(api, method, details):
    r = api.post("/payment/check", json={"payment_method": method, "payment_details": details})

    assert 400 <= r.status_code < 500, f"invalid payment ({method}) must not be approved: {r.status_code} {r.text}"
