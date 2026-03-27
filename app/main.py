import logging

from fastapi import FastAPI
from app.api.routers import router as process_router

logger = logging.getLogger(__name__)

app = FastAPI(title="Multi Agent Review System")

@app.get("/")
def root():
    return {"status": "ok"}

app.include_router(process_router)
