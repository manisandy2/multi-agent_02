import httpx
import json
import logging
import asyncio
from datetime import date
from core.config import settings

logger = logging.getLogger(__name__)


# async def create_complaint(
#     location_name: str,
#     review_date: date,
#     reviewer_name: str,
#     review_text: str,
#     retries: int = 3
# ) -> dict:

#     headers = {
#         "platform": "web",
#         "Authorization": f"App {settings.CRM_AUTH_KEY}",
#     }

#     enquiry_payload = {
#         "cusId": "",
#         "billNo": "",
#         "enquiryFor": "Complaints",
#         "mobileNo": settings.DEFAULT_MOBILE,
#         "branchName": location_name,
#         "subCategory": "Google Review",
#         "callType": 0
#     }

#     complain_payload = {
#         "cusId": "",
#         "party": [],
#         "billNo": "",
#         "enquiryFor": "Complaints",
#         "itemName": "",
#         "billDate": "",
#         "customerName": reviewer_name,
#         "productName": "",
#         "branchName": location_name,
#         "mobileNo": settings.DEFAULT_MOBILE,
#         "subCategory": "Google Review",
#         "complainType": "google_auto_review",
#         "callType": 0,
#         "documentDate": review_date.isoformat(),
#         "itemModelName": "",
#         "itemBrandName": "",
#         "invoiceAmount": "0",
#         "complainAbout": "Others",
#         "complainSource": "Google Review",
#         "complainRecieveDate": review_date.isoformat(),
#         "complaintantExpectation": review_text[:300],
#         "complaintantAdvocateDetails": {}
#     }

#     files = {
#         "enquiry": (None, json.dumps(enquiry_payload)),
#         "complain": (None, json.dumps(complain_payload)),
#     }

#     for attempt in range(retries):
#         try:
#             async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
#                 response = await client.post(
#                     settings.STAGE_URL,
#                     headers=headers,
#                     # files=files
#                 )

#                 logger.info(f"CRM STATUS: {response.status_code}")
#                 logger.info(f"CRM RESPONSE: {response.text}")

#                 response.raise_for_status()

#                 data = response.json()

#                 # ✅ Extract ticket_id safely
#                 ticket_id = (
#                     data.get("ticket_id") or
#                     data.get("id") or
#                     data.get("data", {}).get("id") or
#                     data.get("complaintId")
#                 )

#                 return {
#                     "ticket_id": ticket_id,
#                     "status": "created" if ticket_id else "failed",
#                     "raw": data   # optional (debug)
#                 }

#         except httpx.HTTPStatusError as e:
#             logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")

#         except httpx.RequestError as e:
#             logger.error(f"Network error: {str(e)}")

#         except Exception as e:
#             logger.exception("Unexpected error")

#         await asyncio.sleep(2 ** attempt)

#     return {
#         "ticket_id": None,
#         "status": "failed"
#     }

async def create_complaint(
    auth: str,
    location_name: str,
    review_date: date,
    reviewer_name: str,
    review_text: str,
    url: str = settings.STAGE_URL
) -> dict:

    headers = {
        "platform": "web",
        "Authorization": f"App {auth}",
    }

    enquiry = {
        "cusId": "",
        "billNo": "",
        "enquiryFor": "Complaints",
        "mobileNo": "2320000000",
        "branchName": location_name,
        "subCategory": "Google Review",
        "callType": 0
    }

    complain = {
        "cusId": "",
        "party": [],
        "billNo": "",
        "enquiryFor": "Complaints",
        "itemName": "",
        "billDate": "",
        "customerName": reviewer_name,
        "productName": "",
        "branchName": location_name,
        "mobileNo": "2320000000",
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
        "complaintantAdvocateDetails": {}
    }

    files = {
        "enquiry": (None, json.dumps(enquiry)),
        "complain": (None, json.dumps(complain)),
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()