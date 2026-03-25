from pydantic import BaseModel
from typing import Literal

class SupervisorResponse(BaseModel):
    sentiment: Literal["positive", "neutral", "negative"]
    severity: Literal["low", "medium", "high"]
    action: Literal["reply", "complaint"]
    create_ticket: bool
    reason: str