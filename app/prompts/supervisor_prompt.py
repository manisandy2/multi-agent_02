from .base_prompt import BASE_PROMPT

SUPERVISOR_PROMPT = BASE_PROMPT + """

TASK:
Analyze the review and decide action.

RULES:
- rating <= 2 → negative → complaint → create_ticket=true
- rating == 3 → neutral → reply
- rating >= 4 → positive → reply

OUTPUT (STRICT JSON ONLY):
{
    "sentiment": "positive|neutral|negative",
    "severity": "low|medium|high",
    "action": "reply|complaint",
    "create_ticket": true or false,
    "reason": "short explanation"
}
"""