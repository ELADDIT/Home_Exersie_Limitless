"""Test data builders. Every call returns unique data so parallel runs never collide."""
import uuid
from dataclasses import dataclass, field

from faker import Faker

fake = Faker()

# The API validates that the billing city belongs to the billing country, so we use
# a known-valid address (the one the app's own postcode lookup returns for NL/1012AB).
BILLING_ADDRESS = {
    "street": "Lesingel 8",
    "city": "Steensel",
    "state": "Noord-Holland",
    "country": "NL",
    "postal_code": "1012AB",
}


# Products with special purchase rules that generic pickers must skip (app rule: max one Thor Hammer per customer).
PURCHASE_LIMITED = {"Thor Hammer"}


def strong_password() -> str:
    """Meets the API policy: >= 8 chars, upper + lower case, digit and symbol."""
    return fake.password(length=14, special_chars=True, digits=True, upper_case=True, lower_case=True)


def unique_email() -> str:
    return f"qa.{uuid.uuid4().hex}@example.com"


@dataclass
class Customer:
    first_name: str = field(default_factory=fake.first_name)
    last_name: str = field(default_factory=lambda: fake.last_name()[:20])
    email: str = field(default_factory=unique_email)
    password: str = field(default_factory=strong_password)
    dob: str = "1990-01-15"
    phone: str = "0612345678"
    token: str | None = None  # filled once the customer has logged in via the API
    id: str | None = None

    def registration_payload(self) -> dict:
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "password": self.password,
            "dob": self.dob,
            "phone": self.phone,
            "address": {
                "street": BILLING_ADDRESS["street"],
                "house_number": "8",
                "city": BILLING_ADDRESS["city"],
                "state": BILLING_ADDRESS["state"],
                "country": BILLING_ADDRESS["country"],
                "postal_code": BILLING_ADDRESS["postal_code"],
            },
        }


def billing_payload(cart_id: str, payment_method: str = "cash-on-delivery", payment_details: dict | None = None) -> dict:
    return {
        "billing_street": BILLING_ADDRESS["street"],
        "billing_city": BILLING_ADDRESS["city"],
        "billing_state": BILLING_ADDRESS["state"],
        "billing_country": BILLING_ADDRESS["country"],
        "billing_postal_code": BILLING_ADDRESS["postal_code"],
        "payment_method": payment_method,
        "payment_details": payment_details or {},
        "cart_id": cart_id,
    }
