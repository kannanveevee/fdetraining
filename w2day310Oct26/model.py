"""Data models (shapes of the data) used by the project."""

from pydantic import BaseModel, ConfigDict, Field


class Invoice(BaseModel):
    # One invoice row from data/invoices.json.

    invoice_id: str
    vendor: str
    amount: float | None   # None means the amount is missing
    status: str
    date: str


class Payment(BaseModel):
    # Body of POST /payments. Both fields are required.

    # Example shown in the /docs page.
    model_config = ConfigDict(json_schema_extra={"example": {"invoice_id": "INV-101", "paid": 12000}})

    invoice_id: str = Field(min_length=1)   # cannot be empty
    paid: float = Field(gt=0)               # must be more than 0


class PaymentUpdate(BaseModel):
    # Body of PUT /payments/{index}. Send only the fields you want to change.

    model_config = ConfigDict(json_schema_extra={"example": {"paid": 12000}})

    invoice_id: str | None = Field(default=None, min_length=1)
    paid: float | None = Field(default=None, gt=0)
