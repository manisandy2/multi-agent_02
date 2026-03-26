from fastapi import FastAPI, APIRouter,BackgroundTasks
from datetime import date
from app.queue.worker import process_review_task
from app.agents.supervisor import supervisor_ai
from app.agents.reply_agent import reply_agent
from app.services.crm_service import create_complaint
from app.schemas.review_analysis import ReviewRequest
from app.api.routers import router as process_router

app = FastAPI(title="Multi Agent Review System")
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

@app.get("/")
def root():
    return {"status": "ok"}

app.include_router(process_router)
