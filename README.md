# CodeImpact Backend — Person 3

**Backend & LLM Layer for Grounded Semantic Impact Reasoning**

This service forms the core semantic reasoning layer of CodeImpact. It ingests static graph traversal and retrieved code chunks from **Person 2**, sends evidence to Google Gemini (or the grounded offline evaluator), determines evidence-based risk, extracts claims, and deterministically verifies all citations against source code spans before returning strict JSON to **Person 4**.

---

## Capabilities & Architecture

- **Grounded Semantic Reasoning**: Evaluates *why* code changes propagate downstream through call, inheritance, and import chains.
- **Direct vs. Indirect Propagation**: Distinguishes direct callers (`hop == 1`) from transitive dependents (`hop >= 2`).
- **Semantic Classification**: Identifies `SIGNATURE_CHANGE`, `RETURN_TYPE_CHANGE`, `API_CONTRACT_CHANGE`, `EXCEPTION_BEHAVIOR_CHANGE`, and `LOGIC_IMPACT`.
- **Explainable Risk Rubric**: Cross-references semantic change types and caller volume to compute verifiable risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Citation Range Verification Engine**: Deterministically validates that citations (`file:start_line-end_line`) fall strictly within retrieved chunk spans. The LLM's self-reported citations are never trusted implicitly.
- **Evidence Gap & Contradiction Detection**: Flags missing chunks or mismatches between change summaries and actual source code.

---

## Directory Structure

```text
codeimpact-backend/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Environment and configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ask.py               # POST /ask handler
│   │   └── impact.py            # POST /impact/explain & POST /impact/verify
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py          # Pydantic request models
│   │   └── responses.py         # Pydantic response models
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py              # Base LLM provider interface
│   │   ├── provider.py          # Gemini 2.5 Flash implementation
│   │   └── factory.py           # Provider factory with grounded offline fallback
│   ├── reasoning/
│   │   ├── __init__.py
│   │   ├── impact_engine.py     # Main reasoning orchestrator
│   │   ├── claim_verifier.py    # Deterministic line-range citation verifier
│   │   └── risk_engine.py       # Evidence-based risk rubric
│   └── prompts/
│       ├── __init__.py
│       ├── ask_prompt.py        # System instructions & prompt for Q&A
│       └── impact_prompt.py     # Grounded reasoning prompt with 7-contract schema
├── tests/
│   ├── __init__.py
│   ├── test_api.py              # FastAPI endpoint integration tests
│   ├── test_risk.py             # Risk rubric evaluation tests
│   └── test_verification.py     # Citation range validation tests
├── examples/
│   ├── sample_request.json      # Canonical Person 2 request payload
│   └── sample_response.json     # 7-contract response payload
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable templates
├── .gitignore
└── README.md
```

---

## Endpoints

### 1. `GET /health`
Returns operational health, service version, and LLM readiness:
```json
{
  "status": "ok",
  "service": "codeimpact-backend-person3",
  "version": "1.0.0",
  "llm_status": "connected",
  "has_gemini_key": true,
  "model": "gemini-2.5-flash"
}
```

### 2. `POST /impact/explain`
Primary interface receiving JSON from Person 2:
- **Request Body**:
  - `changed_symbol`: Modified function/class/variable details
  - `impacted_symbols`: Downstream dependencies with hop distance & relation
  - `retrieved_chunks`: Source code chunks with 1-indexed start/end lines
- **Response**: Strict 7-contract JSON containing `summary`, `risk`, `impact_type`, `impact_chain`, `claims`, `confidence`, `uncertainties`, `contradictions`, and deterministic `verified` flag.

### 3. `POST /impact/verify`
Independent verification endpoint:
- **Request Body**:
  - `claims`: Array of statements with `citation` strings (e.g. `"payment.py:87-90"`)
  - `retrieved_chunks`: Ground truth code chunks
- **Response**: Granular validation breakdown for every citation.

### 4. `POST /ask`
Natural language Q&A grounded exclusively in supplied code chunks:
- **Request Body**: `{"query": "...", "retrieved_chunks": [...]}`
- **Response**: `{"answer": "...", "claims": [...], "uncertainties": [...], "verified": true}`

---

## Quick Start & Running

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env and insert your GEMINI_API_KEY
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload
```
Interactive OpenAPI documentation will be available at:
- `http://localhost:3000/docs` (Swagger UI)
- `http://localhost:3000/redoc` (ReDoc)

### 4. Run Tests
```bash
pytest tests/ -v
```
