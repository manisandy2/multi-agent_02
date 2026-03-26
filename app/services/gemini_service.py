import logging
from typing import Optional
from google import genai
from app.core.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_reply(prompt: str) -> Optional[str]:
    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
        )

        if not response.text:
            raise ValueError("Empty response from Gemini")

        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return None