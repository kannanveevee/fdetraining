from fastapi import APIRouter
from pathlib import Path
import json

router = APIRouter()

@router.post("/invoices")
def create_invoice(invoice: dict):
    invoices = load_invoices()
    invoices.append(invoice)
    save_invoices(invoices)
    return invoice

def load_invoices():
    invoices_path = Path(__file__).with_name("invoices.json")
    with invoices_path.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_invoices(invoices):
    invoices_path = Path(__file__).with_name("invoices.json")
    with invoices_path.open("w", encoding="utf-8") as file:
        json.dump(invoices, file, indent=4)