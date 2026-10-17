"""Reads and writes the data (data/invoices.json).

The whole file is loaded into the module variable DATA, which looks like:
    {"invoices": [ {...}, ... ], "payments": [ {...}, ... ]}
All other functions here work on that in-memory DATA.
Changes only reach the disk when save_data() is called.
"""

import json
import os

from model import Invoice


# Full path to data/invoices.json, built from this file's own location so it
# works no matter which folder the program is started from.
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "invoices.json")

# DATA is created by load_data(). It is deliberately not set to {} here, so that
# calling save_data() before loading fails loudly instead of wiping the file.


# ---------- Load / save ----------

def load_data():
    """Read the JSON file into DATA and return it."""
    global DATA
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        DATA = json.load(f)
    return DATA


def save_data():
    """Write the current DATA back to the JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=4)
        return DATA


def get_data():
    return DATA


# ---------- Invoices ----------

def get_invoices():
    """Return all invoices as Invoice objects."""
    return [Invoice(**invoice) for invoice in DATA.get("invoices", [])]


def get_invoice_by_id(invoice_id: str):
    """Return the first invoice with this id, or None."""
    for invoice in DATA.get("invoices", []):
        if invoice.get("invoice_id") == invoice_id:
            return Invoice(**invoice)
    return None


def update_invoice(invoice_id: str, **kwargs):
    """Change fields of an invoice, e.g. update_invoice("INV-1", status="PAID")."""
    for invoice in DATA.get("invoices", []):
        if invoice.get("invoice_id") == invoice_id:
            invoice.update(kwargs)
            return Invoice(**invoice)
    return None


def create_invoice(**kwargs):
    """Add a new invoice (checked by the Invoice model) and return it."""
    invoice = Invoice(**kwargs)
    DATA.get("invoices", []).append(invoice.__dict__)
    return invoice


def delete_invoice(invoice_id: str):
    """Remove the invoice with this id and return it, or None if not found."""
    for i, invoice in enumerate(DATA.get("invoices", [])):
        if invoice.get("invoice_id") == invoice_id:
            return DATA.get("invoices", []).pop(i)
    return None


# ---------- Payments (looked up by invoice_id) ----------

def get_payments():
    return DATA.get("payments", [])


def get_payment_by_invoice_id(invoice_id: str):
    """Return the first payment for this invoice, or None."""
    for payment in DATA.get("payments", []):
        if payment.get("invoice_id") == invoice_id:
            return payment
    return None


def update_payment(invoice_id: str, **kwargs):
    """Change fields of the first payment for this invoice."""
    for payment in DATA.get("payments", []):
        if payment.get("invoice_id") == invoice_id:
            payment.update(kwargs)
            return payment
    return None


def create_payment(**kwargs):
    """Add a new payment, e.g. create_payment(invoice_id="INV-1", paid=500)."""
    payment = kwargs
    DATA.get("payments", []).append(payment)
    return payment


def delete_payment(invoice_id: str):
    """Remove the first payment for this invoice and return it, or None."""
    for i, payment in enumerate(DATA.get("payments", [])):
        if payment.get("invoice_id") == invoice_id:
            return DATA.get("payments", []).pop(i)
    return None


# ---------- Clearing data ----------

def delete_data():
    """Empty DATA completely (in memory only)."""
    DATA.clear()
    return None


def clear_all():
    """Keep the structure but remove every invoice and payment (in memory only)."""
    DATA["invoices"] = []
    DATA["payments"] = []
    return None


# ---------- Payments (looked up by position) ----------
# Payments have no unique id, so the API addresses them by position in the list.
# Valid positions are 0 .. len(payments) - 1; negative numbers are NOT allowed.

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
