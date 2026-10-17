"""GET /invoices and GET /invoices/{invoice_id} - read invoices from invoices.json."""

from fastapi import APIRouter

from invoice_storage import load_invoices

router = APIRouter()


@router.get("/invoices")
def get_invoices():
    # Return every invoice in the file.
    return load_invoices()


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    # Walk through the invoices and return the first one with a matching id.
    for invoice in load_invoices():
        if invoice["invoice_id"] == invoice_id:
            return invoice
    # Not found: note the API answers with a normal 200 response and an error message.
    return {"error": "Invoice not found"}
