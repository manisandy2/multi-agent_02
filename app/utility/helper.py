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
    print(f"Calling Gemini with prompt: '{prompt[:50]}...'")
    for attempt in range(retries):
        try:
            print(f"Attempt {attempt+1} to call Gemini")
            
            response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=[prompt],
                )
                
            if response and getattr(response, "text", None):
                return response
            raise ValueError("Empty response from Gemini")

        except Exception as e:
            logger.warning(f"Gemini retry {attempt+1} failed: {e}")
            if attempt == retries - 1:
                raise

            await asyncio.sleep(2 ** attempt)