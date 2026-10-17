"""Payments API.

This file only handles HTTP: it receives requests, calls the functions in
services.py, and turns errors into proper HTTP error responses.

Run:   uvicorn main:app --reload
Docs:  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException

import repository
import services
from model import Payment, PaymentUpdate

app = FastAPI(title="Payments API")


@app.get("/")
def home():
    # Simple health check that also tells the user where to look next.
    return {
        "message": "Payments API is running",
        "docs": "/docs",
        "payments": "/payments",
    }


@app.on_event("startup")
def startup():
    # Read data/invoices.json into memory once, when the server starts.
    repository.load_data()


def run(func, *args):
    """Call a service function and convert its errors into HTTP errors.

    NotFoundError -> 404, ValueError -> 400, StorageError -> 500.
    This keeps the route functions below short.
    """
    try:
        return func(*args)
    except services.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except services.StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Payments have no id of their own, so {index} is the position in the payments list.

@app.get("/payments")
def list_payments(invoice_id: str | None = None):
    # Optional ?invoice_id=INV-101 filters the list.
    return run(services.list_payments, invoice_id)


@app.get("/payments/{index}")
def get_payment(index: int):
    return run(services.get_payment, index)


@app.post("/payments", status_code=201)
def create_payment(payment: Payment):
    return run(services.add_payment, payment.invoice_id, payment.paid)


@app.put("/payments/{index}")
def update_payment(index: int, changes: PaymentUpdate):
    # exclude_none: only the fields the caller actually sent are changed.
    return run(services.change_payment, index, changes.model_dump(exclude_none=True))


@app.delete("/payments/{index}")
def delete_payment(index: int):
    return run(services.remove_payment, index)
