from .base_prompt import BASE_PROMPT

REPLY_PROMPT = BASE_PROMPT + """

TASK:
Write a professional reply.

RULES:
- Single paragraph
- 3–4 sentences
- Clear and natural tone
- No markdown
- No "Dear"
- No signature/closing
- Do NOT over-apologize

BEHAVIOR:
- Positive → thank the customer and appreciate their feedback
- Neutral → acknowledge feedback and show attentiveness
- Negative → express concern and offer to look into the issue (without making commitments)

STRICT RULES:
- Do NOT promise resolution, refund, or action
- Do NOT assume details not mentioned in the review
- Do NOT admit staff fault directly
- Keep response under 80 words
- Avoid repetitive or generic phrases

GUIDANCE:
- Reference the issue briefly if mentioned
- Encourage the customer to share more details when needed
- Keep tone calm, respectful, and brand-safe

{complaint_instruction}
"""