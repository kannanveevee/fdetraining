import json
import os

from model import Invoice


DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "invoices.json")


def load_data():
    global DATA
    with open(DATA_FILE,"r",encoding="utf-8") as f:
        DATA = json.load(f)
    return DATA

def save_data():
    with open(DATA_FILE,"w",encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=4)
        return DATA

def get_invoices():
    return [Invoice(**invoice) for invoice in DATA.get("invoices", [])]

def get_payments():
    return DATA.get("payments", []) 

def get_invoice_by_id(invoice_id: str):
    for invoice in DATA.get("invoices", []):
        if invoice.get("invoice_id") == invoice_id:
            return Invoice(**invoice)
    return None 

def get_payment_by_invoice_id(invoice_id: str):
    for payment in DATA.get("payments", []):
        if payment.get("invoice_id") == invoice_id:
            return payment
    return None

def get_data():
    return DATA

def update_invoice(invoice_id: str, **kwargs):
    for invoice in DATA.get("invoices", []):
        if invoice.get("invoice_id") == invoice_id:
            invoice.update(kwargs)
            return Invoice(**invoice)
    return None

def update_payment(invoice_id: str, **kwargs):
    for payment in DATA.get("payments", []):
        if payment.get("invoice_id") == invoice_id:
            payment.update(kwargs)
            return payment
    return None

def create_invoice(**kwargs):
    invoice = Invoice(**kwargs)
    DATA.get("invoices", []).append(invoice.__dict__)
    return invoice

def create_payment(**kwargs):
    payment = kwargs
    DATA.get("payments", []).append(payment)
    return payment

def delete_invoice(invoice_id: str):
    for i, invoice in enumerate(DATA.get("invoices", [])):
        if invoice.get("invoice_id") == invoice_id:
            return DATA.get("invoices", []).pop(i)
    return None

def delete_payment(invoice_id: str):
    for i, payment in enumerate(DATA.get("payments", [])):
        if payment.get("invoice_id") == invoice_id:
            return DATA.get("payments", []).pop(i)
    return None

def delete_data():
    DATA.clear()
    return None

def clear_all():
    DATA["invoices"] = []
    DATA["payments"] = []
    return None

# Payments have no unique id, so the API addresses them by position in the list.
def get_payment_by_index(index: int):
    payments = DATA.get("payments", [])
    if 0 <= index < len(payments):
        return payments[index]
    return None

def update_payment_by_index(index: int, **kwargs):
    payment = get_payment_by_index(index)
    if payment is None:
        return None
    payment.update(kwargs)
    return payment

def delete_payment_by_index(index: int):
    payments = DATA.get("payments", [])
    if 0 <= index < len(payments):
        return payments.pop(index)
    return None

