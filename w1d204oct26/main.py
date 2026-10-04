from fastapi import FastAPI
from create_method import router as create_router
from get_method import router as get_router
from delete_method import router as delete_router
# from update_method import router as update_router

app = FastAPI()
app.include_router(create_router)
app.include_router(get_router)
app.include_router(delete_router)
# app.include_router(update_router)

