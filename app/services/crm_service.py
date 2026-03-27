import asyncio
import json
import logging
from datetime import date
from typing import Dict,Any,Optional
 
import httpx
 
from app.core.config import Settings
 
settings = Settings()
logger = logging.getLogger(__name__)
 
 
def _build_headers() -> dict:
    return {
        "platform": "web",
        "Authorization": f"App {settings.CRM_AUTH_KEY}",
    }
 
 
def _build_enquiry_payload(location_name: str) -> dict:
    return {
        "cusId": "",
        "billNo": "",
        "enquiryFor": "Complaints",
        "mobileNo": settings.DEFAULT_MOBILE,
        "branchName": location_name,
        "subCategory": "Google Review",
        "callType": 0,
    }
 
 
def _build_complaint_payload(
    location_name: str,
    reviewer_name: str,
    review_date: date,
    review_text: str,
) -> dict:
    return {
        "cusId": "",
        "party": [],
        "billNo": "",
        "enquiryFor": "Complaints",
        "itemName": "",
        "billDate": "",
        "customerName": reviewer_name,
        "productName": "",
        "branchName": location_name,
        "mobileNo": settings.DEFAULT_MOBILE,
        "subCategory": "Google Review",
        "complainType": "google_auto_review",
        "callType": 0,
        "documentDate": review_date.isoformat(),
        "itemModelName": "",
        "itemBrandName": "",
        "invoiceAmount": "0",
        "complainAbout": "Others",
        "complainSource": "Google Review",
        "complainRecieveDate": review_date.isoformat(),
        "complaintantExpectation": review_text[:300],
        "complaintantAdvocateDetails": {},
    }

def _extract_ticket_id(response: dict) -> Optional[str]:
    return (
        response.get("data", {})
        .get("complainAndEnquirySaved", {})
        .get("complain", {})
        .get("id")
    )

 
async def create_complaint(
    location_name: str,
    reviewer_name: str,
    review_date: date,
    review_text: str,
    job_id: Optional[str] = None,
    url: str = None,
    retries: int = 3,
) -> dict:
    url = url or settings.STAGE_URL
    headers = _build_headers()

    files = {
        "enquiry": (None, json.dumps(_build_enquiry_payload(location_name))),
        "complain": (None, json.dumps(_build_complaint_payload(
            location_name, reviewer_name, review_date, review_text
        ))),
    }
    
    async with httpx.AsyncClient(timeout=10.0, connect=5.0) as client:

        for attempt in range(retries):
            try:
                logger.info(f"[{job_id}] CRM attempt {attempt+1}")

                response = await client.post(url, headers=headers, files=files)
                response.raise_for_status()

                try:
                    data = response.json()
                except Exception:
                    logger.error(f"[{job_id}] Invalid JSON response")
                    return {
                        "status": "failed",
                        "message": "Invalid CRM response format"
                    }

                ticket_id = _extract_ticket_id(data)

                if not ticket_id:
                    logger.error(
                        f"[{job_id}] Missing ticket_id",
                        extra={"response": data}
                    )
                    return {
                        "status": "failed",
                        "message": "Missing ticket_id",
                        "data": data
                    }

                logger.info(f"[{job_id}] Complaint created: {ticket_id}")

                return {
                    "status": "created",
                    "ticket_id": ticket_id,
                    "data": data,
                }

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"[{job_id}] HTTP {e.response.status_code}",
                    extra={"body": e.response.text}
                )

            except httpx.RequestError as e:
                logger.error(f"[{job_id}] Network error: {repr(e)}")

            except Exception:
                logger.exception(f"[{job_id}] Unexpected CRM error")

            # exponential backoff
            await asyncio.sleep(2 ** attempt)

    logger.error(f"[{job_id}] Complaint failed after {retries} retries")

    return {
        "status": "failed",
        "message": "Complaint creation failed after retries"
    }