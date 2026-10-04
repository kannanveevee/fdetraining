import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: str):
    invoices = load_invoices()
    invoice_to_delete = next((invoice for invoice in invoices if invoice["invoice_id"] == invoice_id), None)
    if invoice_to_delete:
        invoices.remove(invoice_to_delete)
        save_invoices(invoices)
        return {"message": "Invoice deleted successfully"}
    return {"message": "Invoice not found"}

def load_invoices():
    invoices_path = Path(__file__).with_name("invoices.json")
    with invoices_path.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_invoices(invoices):
    invoices_path = Path(__file__).with_name("invoices.json")
    with invoices_path.open("w", encoding="utf-8") as file:
        json.dump(invoices, file, indent=4)