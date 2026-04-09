from app.core.config import settings
import asyncio
from google import genai
import logging
from app.core.config import Settings


settings = Settings()
logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def build_complaint_link(ticket_id: str) -> str:
    if not ticket_id:
        return ""
    return f"{settings.ANONYMOUS_LINK}?id={ticket_id}"


