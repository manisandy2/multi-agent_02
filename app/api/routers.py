from fastapi import APIRouter, BackgroundTasks,HTTPException
from app.queue.worker import process_review_task
from app.schemas.review_analysis import ReviewRequest
import logging
import uuid
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/process-review")
async def process_review(
    payload: ReviewRequest, 
    # background_tasks: BackgroundTasks
    ):
    
    try:
        job_id = str(uuid.uuid4())

        data = {
            "job_id": job_id,
            "review": payload.comment,
            "rating": payload.star_rating,
            "reviewer": payload.reviewer,
            "review_date":payload.review_date,
            "location_name": payload.location_name,
        }
        logger.info(f"[{job_id}] Request received")
    except Exception as e:
        logger.exception(f"[{job_id}] Payload error")

        raise HTTPException(
            status_code=400,
            detail={
                "status": "failed",
                "message": "Invalid payload",
                "details": str(e),
            },
        )
    
    try:
        logger.info(f"[{job_id}] process start")
        # background_tasks.add_task(process_review_task, data)
        result = await asyncio.wait_for(process_review_task(data),timeout=30)
        return {
            "job_id": job_id,
            "status": "success",
            "data": result
        }
    
    except asyncio.TimeoutError:
        logger.error(f"[{job_id}] Processing timeout")

        raise HTTPException(
            status_code=504,
            detail={
                "status": "failed",
                "message": "Processing timeout"
            },
        )

    except Exception as e:
        logger.exception(f"[{job_id}] Processing failed")

        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "message": "Internal server error",
                "details": str(e),
            },
        )