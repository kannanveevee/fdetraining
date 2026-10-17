"""DELETE /invoices/{invoice_id} - remove an invoice from invoices.json."""

from fastapi import APIRouter

from invoice_storage import load_invoices, save_invoices

router = APIRouter()


@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: str):
    invoices = load_invoices()

    # Look for the invoice to delete; stays None if there is no match.
    invoice_to_delete = None
    for invoice in invoices:
        if invoice["invoice_id"] == invoice_id:
            invoice_to_delete = invoice
            break

    if invoice_to_delete:
        invoices.remove(invoice_to_delete)
        save_invoices(invoices)
        return {"message": "Invoice deleted successfully"}

    # Not found: the API answers with a normal 200 response and a message.
    return {"message": "Invoice not found"}
