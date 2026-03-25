from fastapi import APIRouter, BackgroundTasks
from app.queue.worker import process_review_task
from app.schemas.review_analysis import ReviewRequest
router = APIRouter()
import logging
import uuid

logger = logging.getLogger(__name__)

@router.post("/process-review")
async def process_review(
    payload: ReviewRequest, 
    background_tasks: BackgroundTasks):
    try:
        job_id = str(uuid.uuid4())

        data = {
            "job_id": job_id,
            "review": payload.comment,
            "rating": payload.star_rating,
            "reviewer": payload.reviewer,
            "location_name": payload.location_name,
        }
        logger.info(f"[{job_id}] Request received")
    except Exception as e:
        logger.error(f"Error starting task: {str(e)}")

        return {
            "status": "failed",
            "error": str(e)
        }
    try:
        background_tasks.add_task(process_review_task, data)
        return {"status": "processing_started"}
    except Exception as e:
        logger.error(f"Error starting task: {str(e)}")
        return {"status": "failed", "error": str(e)}