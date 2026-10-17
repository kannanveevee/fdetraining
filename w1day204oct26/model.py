"""Pydantic model describing an invoice.

Note: the routes currently accept plain dicts, so this model is not used yet.
Its field names (id, customer) also differ from invoices.json (invoice_id, vendor).
"""

from pydantic import BaseModel


class Invoice(BaseModel):
    id: str
    customer: str
    amount: float
    status: str
