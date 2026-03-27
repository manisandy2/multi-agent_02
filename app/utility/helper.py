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


async def _call_gemini(prompt: str, retries: int = 2):
    for attempt in range(retries):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                ),
                timeout=8,
            )
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait_time = 2 ** attempt
            logger.warning(f"Reply retry {attempt+1} failed: {e}")
            await asyncio.sleep(wait_time)