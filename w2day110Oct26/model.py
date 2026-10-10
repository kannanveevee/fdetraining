from pydantic import BaseModel, ConfigDict, Field

class Invoice(BaseModel):
    invoice_id: str
    vendor: str
    amount: float | None
    status: str
    date: str   

class Payment(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"invoice_id": "INV-101", "paid": 12000}})

    invoice_id: str = Field(min_length=1)
    paid: float = Field(gt=0)

class PaymentUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"paid": 12000}})

    invoice_id: str | None = Field(default=None, min_length=1)
    paid: float | None = Field(default=None, gt=0)
