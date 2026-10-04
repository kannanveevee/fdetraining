from pydantic import BaseModel

class Invoice(BaseModel):
    id: str
    customer: str
    amount: float
    status: str
    