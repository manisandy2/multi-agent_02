# from .base_prompt import BASE_PROMPT

# SUPERVISOR_PROMPT = BASE_PROMPT + """

# TASK:
# Analyze the review and decide action.

# RULES:
# - rating <= 2 → negative → complaint → create_ticket=true
# - rating == 3 → neutral → reply
# - rating >= 4 → positive → reply

# OUTPUT (STRICT JSON ONLY):
# {
#     "sentiment": "positive|neutral|negative",
#     "severity": "low|medium|high",
#     "action": "reply|complaint",
#     "create_ticket": true or false,
#     "reason": "short explanation"
# }
# """

from .base_prompt import BASE_PROMPT

SUPERVISOR_PROMPT = BASE_PROMPT + """

TASKS:

INPUT:
- Review: "{review}"
- Rating: {rating}
- Reviewer: "{reviewer}"

1. Classify the review:
   - sentiment (positive | neutral | negative)
   - issue_type (service | staff | product | pricing | hygiene | delay | other)
   - rating (integer from input)

2. Extract key issues:
   - Identify main problems or highlights from the review
   - Keep it concise (max 3 points)

3. Generate a professional response:
   - Polite, brand-safe, and concise
   - Apologize if negative
   - Thank if positive
   - Do NOT mention internal actions like "ticket" or "complaint"

4. Decide action:

RULES:
- rating <= 2 → sentiment = "negative" → action = "complaint" → create_ticket = true
- rating == 3 → sentiment = "neutral" → action = "reply" → create_ticket = false
- rating >= 4 → sentiment = "positive" → action = "reply" → create_ticket = false

SEVERITY RULES:
- negative + strong complaints (fraud, safety, hygiene, rude staff) → high
- negative + normal dissatisfaction → medium
- neutral → low
- positive → low

IMPORTANT:
- Rating is the source of truth (do NOT override using text sentiment)
- If review is empty, rely only on rating
- Do NOT add extra fields
- Do NOT output anything outside JSON
- Keep response under 60 words

OUTPUT (STRICT JSON ONLY):

{{
    "classification": {{
        "sentiment": "positive|neutral|negative",
        "issue_type": "service|staff|product|pricing|hygiene|delay|other",
        "rating": 0
    }},
    "issues": ["point1", "point2", "point3"],
    "severity": "low|medium|high",
    "action": "reply|complaint",
    "create_ticket": true,
    "response": "professional reply text",
    "reason": "short explanation"
}}
"""