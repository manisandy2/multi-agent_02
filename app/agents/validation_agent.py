class ValidationAgent:
    def execute(self, state):
        text = state.response.lower()

        if state.sentiment == "negative" and "sorry" not in text:
            state.response = "We sincerely apologize. " + state.response

        if state.sentiment != "negative" and "thank" not in text:
            state.response = "Thank you for your feedback. " + state.response

        state.logs.append("ValidationAgent done")
        return state