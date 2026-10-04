import json 
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

@router.get("/invoices")
def get_invoices():
    return load_invoices()

@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    for invoice in load_invoices():
        if invoice["invoice_id"] == invoice_id:
            return invoice
    return {"error": "Invoice not found"}

# read invoices from json
def load_invoices():
    invoices_path = Path(__file__).with_name("invoices.json")
    with invoices_path.open("r", encoding="utf-8") as file:
        return json.load(file)
    
