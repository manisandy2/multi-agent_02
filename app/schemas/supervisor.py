from pydantic import BaseModel
from typing import Literal

# class SupervisorResponse(BaseModel):
#     sentiment: Literal["positive", "neutral", "negative"]
#     severity: Literal["low", "medium", "high"]
#     action: Literal["reply", "complaint"]
#     create_ticket: bool
#     reason: str

class Classification(BaseModel):
    sentiment: str
    issue_type: str
    rating: int

class SupervisorResponse(BaseModel):
    classification: Classification
    issues: list[str]
    severity: str
    action: str
    create_ticket: bool
    response: str
    reason: str