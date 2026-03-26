# import httpx
# import json
# import logging
# import asyncio
# from datetime import date
# from app.core.config import Settings

# settings = Settings()
# logger = logging.getLogger(__name__)


# async def create_complaint(
#     auth: str,
#     location_name: str,
#     review_date: date,
#     reviewer_name: str,
#     review_text: str,
#     url: str = settings.STAGE_URL,
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
#         "mobileNo": settings.DEFAULT_MOBILE,   # ✅ config
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

#     # 🔁 Retry logic
#     for attempt in range(retries):
#         try:
#             async with httpx.AsyncClient(timeout=10.0) as client:
#                 response = await client.post(
#                     url,
#                     headers=headers,
#                     files=files
#                 )

#                 response.raise_for_status()

#                 try:
#                     data = response.json()
#                 except Exception:
#                     logger.error("Invalid JSON response")
#                     return {"status": "error", "message": "Invalid response format"}

#                 logger.info(f"Complaint created for {location_name}")

#                 return {
#                     "status": "success",
#                     "data": data
#                 }

#         except httpx.HTTPStatusError as e:
#             logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")

#         except httpx.RequestError as e:
#             logger.error(f"Network error: {str(e)}")

#         except Exception as e:
#             logger.exception("Unexpected error")

#         # ⏳ Exponential backoff
#         await asyncio.sleep(2 ** attempt)

#     # ❌ Final failure
#     return {
#         "status": "failed",
#         "message": "Complaint creation failed after retries"
#     }

import asyncio
import json
import logging
from datetime import date
 
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
 
 
async def create_complaint(
    location_name: str,
    reviewer_name: str,
    review_date: date,
    review_text: str,
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
 
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, files=files)
                response.raise_for_status()
 
                try:
                    data = response.json()
                    print(data)
                except Exception:
                    logger.error("Invalid JSON in CRM response")
                    return {"status": "error", "message": "Invalid response format"}
 
                logger.info(f"Complaint created for {location_name}")
                return {"status": "success", "data": data}
 
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Network error: {e}")
        except Exception:
            logger.exception("Unexpected error during complaint creation")
 
        await asyncio.sleep(2 ** attempt)
 
    logger.error(f"Complaint creation failed after {retries} attempts")
    return {"status": "failed", "message": "Complaint creation failed after retries"}