"""Response schemas. `Model.model_validate(json)` fails with a precise message if the
API drops a field or changes its type. Only fields we rely on are declared; extra
fields are allowed so harmless additions don't break the suite."""
from pydantic import BaseModel, ConfigDict


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class Named(_Base):
    id: str
    name: str


class Product(_Base):
    id: str
    name: str
    description: str
    price: float
    in_stock: bool
    is_rental: bool
    category: Named
    brand: Named


class Page(_Base):
    current_page: int
    last_page: int
    per_page: int
    total: int


class ProductPage(Page):
    data: list[Product]


class CartItem(_Base):
    id: str
    quantity: int
    product_id: str
    product: Product


class Cart(_Base):
    id: str
    cart_items: list[CartItem]


class Invoice(_Base):
    id: str
    invoice_number: str
    user_id: str | None = None
    billing_city: str
    billing_country: str
    subtotal: float | None = None
    total: float


class InvoicePage(Page):
    data: list[Invoice]


class LoginToken(_Base):
    access_token: str
    token_type: str
    expires_in: int


class User(_Base):
    id: str
    first_name: str
    last_name: str
    email: str
