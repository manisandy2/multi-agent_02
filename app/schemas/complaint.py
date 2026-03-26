import httpx
import json
import logging
import asyncio
from datetime import date
from core.config import settings

logger = logging.getLogger(__name__)




# async def create_complaint(
#     auth: str,
#     location_name: str,
#     review_date: date,
#     reviewer_name: str,
#     review_text: str,
#     url: str = settings.STAGE_URL
# ) -> dict:

#     headers = {
#         "platform": "web",
#         "Authorization": f"App {auth}",
#     }

#     enquiry = {
#         "cusId": "",
#         "billNo": "",
#         "enquiryFor": "Complaints",
#         "mobileNo": "2320000000",
#         "branchName": location_name,
#         "subCategory": "Google Review",
#         "callType": 0
#     }

#     complain = {
#         "cusId": "",
#         "party": [],
#         "billNo": "",
#         "enquiryFor": "Complaints",
#         "itemName": "",
#         "billDate": "",
#         "customerName": reviewer_name,
#         "productName": "",
#         "branchName": location_name,
#         "mobileNo": "2320000000",
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
#         "enquiry": (None, json.dumps(enquiry)),
#         "complain": (None, json.dumps(complain)),
#     }

#     async with httpx.AsyncClient(timeout=10.0) as client:
#         response = await client.post(url, headers=headers, files=files)
#         response.raise_for_status()
#         return response.json()