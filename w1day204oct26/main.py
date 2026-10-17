"""Invoice API entry point.

Each file (create_method, get_method, delete_method) defines the routes for
one kind of request. This file just plugs them all into one FastAPI app.

Run:  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI

from create_method import router as create_router
from get_method import router as get_router
from delete_method import router as delete_router
# from update_method import router as update_router   # update route not written yet

app = FastAPI()

app.include_router(create_router)   # POST   /invoices
app.include_router(get_router)      # GET    /invoices and /invoices/{invoice_id}
app.include_router(delete_router)   # DELETE /invoices/{invoice_id}
# app.include_router(update_router)
