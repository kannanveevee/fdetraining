"""POST /invoices - add a new invoice to invoices.json."""

from fastapi import APIRouter

# load_invoices / save_invoices are imported so they can still be used
# as create_method.load_invoices and create_method.save_invoices.
from invoice_storage import load_invoices, save_invoices

router = APIRouter()


@router.post("/invoices")
def create_invoice(invoice: dict):
    # 1. read what is already stored
    invoices = load_invoices()
    # 2. add the new invoice at the end of the list
    invoices.append(invoice)
    # 3. write the updated list back to the file
    save_invoices(invoices)
    # 4. send the new invoice back to the caller
    return invoice
