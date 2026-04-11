# 🚀 Multi-Agent Review Processing System

This project implements a **Multi-Agent System** to process customer reviews and generate intelligent, brand-compliant responses.

## 🤖 Agents Used

- **Agent 1** → Decision + Draft Reply Generator  
- **Agent 2** → Supervisor / Compliance Validator  

---

## 📌 Features

- Sentiment Analysis (Positive / Neutral / Negative)
- Issue Detection (max 3 issues)
- Draft Reply Generation
- Brand Compliance Validation
- Retry & Fallback Handling
- Clean State Management

---

## 🏗️ Architecture Overview

```code 
Client Request (API)
         ↓
FastAPI Endpoint (/process-review)
         ↓
ReviewState Initialization
         ↓
Agent 1 (Decision + Draft Reply)
         ↓
Agent 2 (Supervisor / Validator)
         ↓
Final Response

```
---

## 📂 Project Structure

```code 
app/
│
├── main.py # FastAPI entry point
├── models/
│ └── request.py # Request schema
│
├── state/
│ └── review_state.py # Shared state object
│
├── agents/
│ ├── decision_agent.py # Agent 1
│ └── supervisor_agent.py # Agent 2
│
├── services/
│ └── orchestrator.py # Pipeline controller
│
├── utils/
│ └── logger.py # Logging utilities
```

---

## 🔷 API Endpoint

### POST `/process-review`

### 📥 Request Body

```json
{
  "comment": "Service was very slow",
  "star_rating": 1,
  "reviewer": "John",
  "location_name": "Anna Nagar",
  "review_date": "2024-01-01"
}
```
### 📤 Response Format

---
```code
{
  "status": "success",
  "data": {
    "sentiment": "negative",
    "issue_type": "service",
    "issues": ["slow service"],
    "reply": "We’re sorry for your experience..."
  }
}
```

---
# 🔷 Core Components
## 1. 🧠 ReviewState (State Management)

Central object shared across agents.

```code
class ReviewState:
    review: str
    rating: int
    reviewer: str
    store: str

    sentiment: str = None
    issue_type: str = None
    issues: list = []

    draft_reply: str = None
    final_reply: str = None

    retry_count: dict = {}
```
---
### 2. 🤖 Agent 1 — Decision + Draft Reply
---
***Responsibilities:***

- Classify sentiment
- Detect issue type
- Extract up to 3 issues
- Generate draft reply

Output:

- sentiment
- issue_type
- issues
- draft_reply
---
## 3. 🛡️ Agent 2 — Supervisor / Validator

Responsibilities:

- Validate draft reply
- Apply brand tone
- Fix issues if needed
- Provide fallback on failure

## ⚠️ Important Rule:
### Agent 2 does NOT generate from scratch — only validates and corrects.
---

# 4. 🔄 Orchestrator (Pipeline)
```code 
async def process_pipeline(state: ReviewState):
    await decision_agent(state)
    await supervisor_agent(state)
    return state
🔁 Retry & Error Handling
max_retries = 2

for attempt in range(max_retries):
    try:
        # agent execution
        break
    except Exception:
        state.increment_retry("agent_name")
Fallback
Returns safe default response
Example: "Fallback due to error"
```
# 🧾 Logging

Each stage logs progress:

```code 
state.log("Reply generation started")
state.log("Supervisor validation completed")

```
### 🔄 End-to-End Flow

```code 
User Request
   ↓
API Layer
   ↓
ReviewState Created
   ↓
Agent 1
   → sentiment
   → issues
   → draft reply
   ↓
Agent 2
   → validate
   → correct
   ↓
Final Response
   ↓
Return to Client

```
## ✅ Design Principles
```text Agent Separation
Agent 1 → Processing
Agent 2 → Validation
State-Driven Architecture
No global variables
Everything flows through ReviewState
Retry Safe
Each agent is isolated
Extensible

```
# 🛠️ Setup Instructions
### Clone repo
```code
git clone https://github.com/manisandy2/multi-agent_02.git

cd multi-agent_02

# Create virtual environment
python -m venv venv

# Activate environment
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload

```
## 👨‍💻 Author

### Manikandan R.
Backend Developer | Multi-Agent Systems | AWS | Python

## 📄 License

This project is open-source and available under the MIT License.