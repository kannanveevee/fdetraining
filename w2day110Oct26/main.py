from fastapi import FastAPI, HTTPException

import repository
import services
from model import Payment, PaymentUpdate

app = FastAPI(title="Payments API")


@app.get("/")
def home():
    return {
        "message": "Payments API is running",
        "docs": "/docs",
        "payments": "/payments",
    }


@app.on_event("startup")
def startup():
    repository.load_data()


def run(func, *args):
    try:
        return func(*args)
    except services.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except services.StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/payments")
def list_payments(invoice_id: str | None = None):
    return run(services.list_payments, invoice_id)


@app.get("/payments/{index}")
def get_payment(index: int):
    return run(services.get_payment, index)


@app.post("/payments", status_code=201)
def create_payment(payment: Payment):
    return run(services.add_payment, payment.invoice_id, payment.paid)


@app.put("/payments/{index}")
def update_payment(index: int, changes: PaymentUpdate):
    return run(services.change_payment, index, changes.model_dump(exclude_none=True))


@app.delete("/payments/{index}")
def delete_payment(index: int):
    return run(services.remove_payment, index)
