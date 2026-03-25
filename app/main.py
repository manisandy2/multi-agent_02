from fastapi import FastAPI, APIRouter,BackgroundTasks
from datetime import date
from app.queue.worker import process_review_task
from app.agents.supervisor import supervisor_ai
from app.agents.reply_agent import reply_agent
from app.services.crm_service import create_complaint
from app.schemas.review_analysis import ReviewRequest

app = FastAPI(title="Multi Agent Review System")
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()

@app.get("/")
def root():
    return {"status": "ok"}


# @app.post("/processes-review")
# async def process_review(payload: dict, background_tasks: BackgroundTasks):

#     review = payload.get("comment", "")
#     rating = int(payload.get("star_rating", 3))
#     name = payload.get("reviewer", "Customer")
#     location = payload.get("location_name", "Store")
#     review_date = payload.get("review_date")

#     # 🧠 Step 1: Supervisor Decision
#     decision = await supervisor_ai(review, rating)

#     # 🚨 Step 2: Complaint Flow
#     if decision.get("create_ticket"):

#         background_tasks.add_task(
#             create_complaint,
#             auth="your_auth_key",
#             location_name=location,
#             review_date=date.fromisoformat(review_date),
#             reviewer_name=name,
#             review_text=review,
#         )

#         return {
#             "status": "complaint_processing",
#             "decision": decision
#         }

#     # ✍️ Step 3: Reply Flow
#     result = reply_agent(review, rating, name, location)

#     return {
#         "status": "reply_generated",
#         "decision": decision,
#         "result": result
#     }

@app.post("/process-review")
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
        logger.info(f"[{job_id}] process start")
        # background_tasks.add_task(process_review_task, data)
        result = await process_review_task(data)
        return result
    except Exception as e:
        logger.error(f"Error starting task: {str(e)}")
        return {"status": "failed", "error": str(e)}