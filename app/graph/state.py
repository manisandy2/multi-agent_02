from typing import TypedDict, Optional,Dict


class ReviewState(TypedDict):
    review: str
    rating: int
    reviewer: str
    location_name: str
    review_date: str

    decision: Optional[Dict]
    ticket: Optional[Dict]
    reply: Optional[str]

    status: Optional[str]