import httpx
import os
import logging
from app.core.config import Settings

settings = Settings()

logger = logging.getLogger(__name__)

CRM_URL = settings.STAGE_URL

async def complaint_agent(data):
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT) as client:
            response = await client.post(CRM_URL, json=data)

            response.raise_for_status()

            result = response.json()

            ticket_id = result.get("ticket_id") or result.get("id")

            if not ticket_id:
                raise ValueError("Ticket ID missing in CRM response")

            return {
                "ticket_id": ticket_id,
                "status": "created"
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"CRM HTTP error: {e.response.text}")

    except Exception as e:
        logger.error(f"CRM error: {e}")

    # ✅ fallback (never crash system)
    return {
        "ticket_id": None,
        "status": "failed"
    }