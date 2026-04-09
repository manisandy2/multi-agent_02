class State:
    def __init__(self, review, rating, reviewer, store):
        self.review = review
        self.rating = rating
        self.reviewer = reviewer
        self.store = store

        self.sentiment = None
        self.issues = []
        self.action = None
        self.response = None
        self.ticket_id = None

        self.logs = []