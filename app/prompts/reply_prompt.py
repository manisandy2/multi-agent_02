from .base_prompt import BASE_PROMPT

REPLY_PROMPT = BASE_PROMPT + """

TASK:
Write a professional reply.

RULES:
- Single paragraph
- 60–80 words
- No markdown
- No "Dear"
- No closing
- Do NOT over-apologize

BEHAVIOR:
- Positive → thank customer
- Neutral → acknowledge feedback
- Negative → apologize and assure resolution

{complaint_instruction}
"""