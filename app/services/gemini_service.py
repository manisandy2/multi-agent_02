from google import genai
import os
import logging
from app.core.config import Settings
logger = logging.getLogger(__name__)

settings = Settings()

client = genai.Client(api_key=settings.GEMINI_API_KEY)



def generate_reply(prompt: str) -> str:
    try:
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = model.generate_content(prompt)

        if not response.text:
            raise ValueError("Empty response")

        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return None